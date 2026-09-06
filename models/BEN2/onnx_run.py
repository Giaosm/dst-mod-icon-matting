import onnxruntime
import numpy as np
from PIL import Image
import torchvision.transforms as transforms
import torch
import torch.nn.functional as F


session = onnxruntime.InferenceSession("./BEN2_Base.onnx", providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])

def postprocess_image(result_np: np.ndarray, im_size: list) -> np.ndarray:

    result = torch.from_numpy(result_np)
    

    if len(result.shape) == 3:
        result = result.unsqueeze(0)
    

    result = torch.squeeze(F.interpolate(result, size=im_size, mode='bilinear'), 0)
    

    ma = torch.max(result)
    mi = torch.min(result)
    result = (result - mi) / (ma - mi)
    
    im_array = (result * 255).permute(1, 2, 0).cpu().data.numpy().astype(np.uint8)
    im_array = np.squeeze(im_array)
    return im_array

def preprocess_image(image):
    original_size = image.size
    transform = transforms.Compose([
        transforms.Resize((1024, 1024)),
        transforms.ToTensor(),
    ])
    img_tensor = transform(image)

    img_tensor = img_tensor.unsqueeze(0)
    return img_tensor.numpy(), image, original_size

def run_inference(image):

    input_data, original_image, (w, h) = preprocess_image(image)

    input_name = session.get_inputs()[0].name
    
    outputs = session.run(None, {input_name: input_data})
    

    alpha = postprocess_image(outputs[0], im_size=[w, h])
    

    mask = Image.fromarray(alpha)
    mask = mask.resize((w, h))
    

    original_image.putalpha(mask)
    return original_image

# Example usage
image_path = "image.png"
output_path = "output.png"


image = Image.open(image_path)

result_image = run_inference(image)
result_image.save(output_path)
