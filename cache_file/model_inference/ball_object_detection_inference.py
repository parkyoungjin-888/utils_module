import numpy as np
import onnxruntime as ort
from typing import Type
from pydantic import BaseModel
from config_module.config_singleton import ConfigSingleton
from mongodb_module.beanie_client import CollectionClient
from kafka_module.kafka_producer import KafkaProducerControl
from datetime import datetime, timezone


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
                 collection_client: CollectionClient = None):
        config = ConfigSingleton()

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

        self.collection_client = collection_client
        kafka_server_urls = config.get_value('kafka').get('server_urls')
        self.kafka_producer = KafkaProducerControl(server_urls=kafka_server_urls, topic='ImageResult')

    def preprocess_img(self, img):
        crop_img = img[120:600, 320:960]
        img_array = np.array(crop_img, dtype=np.float32)
        img_array = (img_array / 255.0 - self.mean) / self.std
        img_array = np.transpose(img_array, (2, 0, 1))
        img_array = np.expand_dims(img_array, axis=0)
        return img_array.astype(np.float32)

    async def run(self, messages: dict):
        if messages is None:
            return
        elif messages.get('device_id') != 'cam2':
            return

        img_data = self.data_model(**messages, stringify_extra_type=True).get_dict_with_img_decoding()
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

        obj_box = {}
        if len(max_boxes) > 0:
            i = 0
            rescale_max_boxes = rescale_bboxes(max_boxes, self.input_size)
            for label, box in zip(max_label, rescale_max_boxes):
                x_1, y_1, x_2, y_2 = (box + [320, 120, 320, 120]).astype(np.int32)
                obj_box.update({
                    f'dec_{i}_label': int(label),
                    f'dec_{i}_x1': int(x_1),
                    f'dec_{i}_y1': int(y_1),
                    f'dec_{i}_x2': int(x_2),
                    f'dec_{i}_y2': int(y_2),
                    f'dec_{i}_cx': int((x_1 + x_2) / 2),
                    f'dec_{i}_cy': int((y_1 + y_2) / 2),
                })
                i += 1

            collection_req = {'query': {'name': img_data['name']},
                              'set': {
                                  'name': img_data['name'],
                                  'result.obj_box': obj_box,
                                  'updated_datetime': datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                              },
                              'upsert': True}
            collection_res = await self.collection_client.update_one(**collection_req)

            str_format = '%Y-%m-%dT%H:%M:%SZ'
            event_datetime_str = datetime.fromtimestamp(img_data['timestamp'], tz=timezone.utc).strftime(str_format)
            producing_payload = {'name': img_data['name'], 'event_datetime_str': event_datetime_str, **obj_box}
            self.kafka_producer.send(producing_payload)
