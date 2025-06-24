from portabletorch import PortableTorch
import torch
#import model
import cnn

# Create torch model and save file
#m = model.Model()
m = cnn.CNN(15)
torch.save(m.state_dict(),"model.pt")
# Add extra data. Read model.py to get shape info.
dirname = "mymodel"
#model_path = "model.py"
model_path = "cnn.py"
#input_shape = (2)
input_shape = (1,15,5,5)
output_shape = (1)
# Create portable torch model
p = PortableTorch(
    m,
    #"Model",
    "CNN",
    model_path,
    dependence_paths=[],
    #args=[],
    args=[15],
    kwargs={},
    input_shape=input_shape,
    output_shape=output_shape,
    #comment="Simplest example. No extra files (dependencies) or arguments to the model constructor of either type (args nor kwargs).")
    comment="Convolutional example with one positional argument in constructor")
# Save to directory
p.save("mymodel")
# Test
p.print()
p.test()
