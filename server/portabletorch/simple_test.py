from portabletorch import PortableTorch
import torch
import model

# Create torch model and save file
m = model.Model()
torch.save(m.state_dict(),"model.pt")
# Add extra data. Read model.py to get shape info.
dirname = "mymodel"
model_path = "model.py"
input_shape = (2)
output_shape = (1)
# Create portable torch model
p = PortableTorch(
    m,
    "Model",
    model_path,
    dependence_paths=[],
    args=[],
    kwargs={},
    input_shape=input_shape,
    output_shape=output_shape,
    comment="Simplest example. No extra files (dependencies) or arguments to the model constructor of either type (args nor kwargs)."
)
# Save to directory
p.save("mymodel")
# Test
p.print()
p.test()
