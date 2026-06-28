import os
import sys

# We will try to import torch. If not available, we will install it temporarily or create a mock file.
try:
    import torch
    import torch.nn as nn
except ImportError:
    print("Installing torch to generate the policy...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "torch", "--quiet"])
    import torch
    import torch.nn as nn

class MARLPolicy(nn.Module):
    def __init__(self):
        super(MARLPolicy, self).__init__()
        # Inputs: 10 features (x, y, velocity, heart_rate, 6 team formation coords)
        # Outputs: 8 features (5 for action logits, 1 for confidence, 2 for predicted X/Y offsets)
        self.fc = nn.Sequential(
            nn.Linear(10, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 8)
        )

    def forward(self, x):
        return self.fc(x)

def main():
    model = MARLPolicy()
    model.eval()
    
    # Save the model
    output_path = os.path.join(os.path.dirname(__file__), "marl_policy.pt")
    torch.save(model, output_path)
    print(f"Policy saved successfully to {output_path}")

if __name__ == "__main__":
    main()
