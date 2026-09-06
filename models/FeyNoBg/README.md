---
library_name: nobg
tags:
- nobg-birefnet
- model_hub_mixin
- nobg
- pytorch_model_hub_mixin
license: apache-2.0
---

<p align="center">
<img src="https://usefeyn.com/feyn/feyn_mark.svg"/>
</p>

This model has been pushed to the Hub using the [PytorchModelHubMixin](https://huggingface.co/docs/huggingface_hub/package_reference/mixins#huggingface_hub.PyTorchModelHubMixin) integration.

Library: [nobg](https://github.com/feyninc/nobg)

Blog : [feynobg blogpost](https://usefeyn.com/blog/feynobg/) [HF blogpost](https://huggingface.co/blog/feyninc/feynobg)


## how to use the model
```
pip install nobg>=0.2.5
```

```python
import torch
from loadimg import load_img
from nobg import AutoModel, AutoProcessor

model = AutoModel.from_pretrained("feyninc/FeyNobg").eval()
processor = AutoProcessor.from_pretrained("feyninc/FeyNobg")

image = load_img("input.jpg").convert("RGB")
inputs = processor(image, return_tensors="pt")

with torch.no_grad():
    outputs = model(pixel_values=inputs["pixel_values"])

alpha = processor.post_process_alpha_matting(
    outputs, target_sizes=[(image.height, image.width)]
)[0]
processor.cutout(image, alpha).save("output.png")
```


![image](https://cdn-uploads.huggingface.co/production/uploads/6527e89a8808d80ccff88b7a/2QIFDxrIJCLlXY87vOzH2.png)

![image](https://cdn-uploads.huggingface.co/production/uploads/6527e89a8808d80ccff88b7a/W0rNUdiP56son6i33vHzY.png)

![image](https://cdn-uploads.huggingface.co/production/uploads/6527e89a8808d80ccff88b7a/ohqZF89NGEm5LXrEOMLP0.png)

## Citation
If you use this model, please cite:
```bibtex
@article{zheng2024birefnet,
  title={Bilateral Reference for High-Resolution Dichotomous Image Segmentation},
  author={Zheng, Peng and Gao, Dehong and Fan, Deng-Ping and Liu, Li and Laaksonen, Jorma and Ouyang, Wanli and Sebe, Nicu},
  journal={CAAI Artificial Intelligence Research},
  volume={3},
  pages={9150038},
  year={2024},
  url={https://arxiv.org/abs/2401.03407},
}
```

## Contributions
Any contributions are welcome at https://github.com/feyninc/nobg