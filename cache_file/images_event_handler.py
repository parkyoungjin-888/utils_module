import time
import cv2
import numpy as np
import onnxruntime as ort
from typing import Type
from pydantic import BaseModel
import boto3
from io import BytesIO
from mongodb_module.beanie_client import CollectionClient
import asyncio


def box_cxcywh_to_xyxy(box_array):
    box_array = np.asarray(box_array)
    x_c, y_c, w, h = box_array[:, 0], box_array[:, 1], box_array[:, 2], box_array[:, 3]
    b = np.stack([
        x_c - 0.5 * w,  # x_min
        y_c - 0.5 * h,  # y_min
        x_c + 0.5 * w,  # x_max
        y_c + 0.5 * h  # y_max
    ], axis=1)
    return b


def rescale_bboxes(out_bbox, size):
    img_w, img_h = size
    b = box_cxcywh_to_xyxy(out_bbox)
    b = b * np.array([img_w, img_h, img_w, img_h], dtype=np.float32)
    return b


class ModelInference:
    def __init__(self, data_model: Type[BaseModel], onnx_model_path: str,
                 s3_client: boto3.client, collection_client: CollectionClient = None):
        self.data_model = data_model
        self.input_size = (640, 480)
        session_options = ort.SessionOptions()
        session_options.intra_op_num_threads = 8
        session_options.inter_op_num_threads = 8
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        # print("Available providers:", ort.get_available_providers())
        self.session = ort.InferenceSession(onnx_model_path, sess_options=session_options, providers=providers)
        self.input_name = self.session.get_inputs()[0].name

        self.mean = [0.485, 0.456, 0.406]
        self.std = [0.229, 0.224, 0.225]

        # print("Execution Providers:", self.session.get_providers())
        # print(ort.get_device())

        self.s3_client = s3_client
        self.collection_client = collection_client

    def preprocess_img(self, img):
        crop_img = img[120:600, 320:960]
        img_array = np.array(crop_img, dtype=np.float32)
        img_array = (img_array / 255.0 - self.mean) / self.std
        img_array = np.transpose(img_array, (2, 0, 1))
        img_array = np.expand_dims(img_array, axis=0)
        return img_array.astype(np.float32)

    def run(self, messages: dict):
        if messages is None:
            return
        elif messages.get('cam2') != 'cam2':
            return

        start = time.time()
        img_data = self.data_model(**messages).get_dict_with_img_decoding()
        img_array = self.preprocess_img(img_data['img'])

        outputs = self.session.run(None, {self.input_name: img_array})

        predicted_labels = np.squeeze(outputs[0])

        exps = np.exp(predicted_labels)
        softmax_result = (exps / np.sum(exps, axis=-1, keepdims=True))[:, :-1]

        threshold = 0.7
        max_values = np.max(softmax_result, axis=-1)
        indices = np.where(max_values >= threshold)
        max_label = [np.argmax(predicted_labels[idx], axis=-1) for idx in zip(*indices)]

        predicted_boxes = np.squeeze(outputs[1])
        max_boxes = [predicted_boxes[idx] for idx in zip(*indices)]

        obj_box = []
        if len(max_boxes) > 0:
            rescale_max_boxes = rescale_bboxes(max_boxes, self.input_size)
            for label, box in zip(max_label, rescale_max_boxes):
                x_1, y_1, x_2, y_2 = (box + [320, 120, 320, 120]).astype(np.int32)
                obj_box.append([[x_1, y_1], [x_2, y_2], label])
                cv2.rectangle(img_data['img'], (320, 120), (960, 600), (0, 0, 255), 1)
                cv2.rectangle(img_data['img'], (x_1, y_1), (x_2, y_2), (0, 255, 0), 1)
                cv2.putText(img_data['img'], str(label), (x_1, y_1), cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 1)
            tact = str(time.time() - start)
            cv2.putText(img_data['img'], tact, (50, 50), cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 1)
            # cv2.imshow('img', img_data['img'])
            # cv2.waitKey(1)
            # cv2.imwrite('./result/re' + img_data['name'], img_data['img'])

            collection_req = {'query': {'name': img_data['name']}, 'set': {'result.obj_box': obj_box}, 'upsert': True}
            collection_res = asyncio.run(self.collection_client.update_one(collection_req))
            # print(collection_res)

            _, jpeg_image = cv2.imencode('.jpg', img_data['img'])
            image_bytes = BytesIO(jpeg_image.tobytes())
            img_path = f"{img_data['device_id']}/{img_data['name']}"
            s3_res = self.s3_client.upload_fileobj(image_bytes, 'resultimages', img_path)
            # print(s3_res)
