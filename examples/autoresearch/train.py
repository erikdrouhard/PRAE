"""Example training script — the mutable surface for PRAE's proving ground.

This is a deliberately simple script that trains a tiny model and prints a metric.
PRAE will modify this file to try to improve the metric.
"""

import random
import math

# Hyperparameters (PRAE's mutable surface)
LEARNING_RATE = 0.1
BATCH_SIZE = 32
EPOCHS = 50
HIDDEN_SIZE = 16

def generate_data(n=200):
    """Generate a simple binary classification dataset."""
    data = []
    for _ in range(n):
        x1 = random.gauss(0, 1)
        x2 = random.gauss(0, 1)
        label = 1 if x1 * x2 > 0 else 0
        data.append(([x1, x2], label))
    return data

def sigmoid(x):
    x = max(-500, min(500, x))
    return 1.0 / (1.0 + math.exp(-x))

def train():
    random.seed(42)
    data = generate_data()
    split = int(len(data) * 0.8)
    train_data = data[:split]
    test_data = data[split:]

    # Simple 2-layer network: 2 -> HIDDEN_SIZE -> 1
    w1 = [[random.gauss(0, 0.5) for _ in range(2)] for _ in range(HIDDEN_SIZE)]
    b1 = [0.0] * HIDDEN_SIZE
    w2 = [random.gauss(0, 0.5) for _ in range(HIDDEN_SIZE)]
    b2 = 0.0

    for epoch in range(EPOCHS):
        random.shuffle(train_data)
        total_loss = 0.0

        for i in range(0, len(train_data), BATCH_SIZE):
            batch = train_data[i:i + BATCH_SIZE]

            for inputs, label in batch:
                # Forward
                hidden = []
                for j in range(HIDDEN_SIZE):
                    h = b1[j] + sum(w1[j][k] * inputs[k] for k in range(2))
                    hidden.append(max(0, h))  # ReLU

                out = b2 + sum(w2[j] * hidden[j] for j in range(HIDDEN_SIZE))
                pred = sigmoid(out)

                # Loss
                eps = 1e-7
                loss = -(label * math.log(pred + eps) + (1 - label) * math.log(1 - pred + eps))
                total_loss += loss

                # Backward (simplified SGD)
                d_out = pred - label

                for j in range(HIDDEN_SIZE):
                    d_w2 = d_out * hidden[j]
                    w2[j] -= LEARNING_RATE * d_w2
                    if hidden[j] > 0:
                        for k in range(2):
                            d_w1 = d_out * w2[j] * inputs[k]
                            w1[j][k] -= LEARNING_RATE * d_w1
                        b1[j] -= LEARNING_RATE * d_out * w2[j]

                b2 -= LEARNING_RATE * d_out

        avg_loss = total_loss / len(train_data)

    # Evaluate on test set
    test_loss = 0.0
    correct = 0
    for inputs, label in test_data:
        hidden = []
        for j in range(HIDDEN_SIZE):
            h = b1[j] + sum(w1[j][k] * inputs[k] for k in range(2))
            hidden.append(max(0, h))
        out = b2 + sum(w2[j] * hidden[j] for j in range(HIDDEN_SIZE))
        pred = sigmoid(out)
        eps = 1e-7
        test_loss += -(label * math.log(pred + eps) + (1 - label) * math.log(1 - pred + eps))
        if (pred > 0.5) == (label == 1):
            correct += 1

    test_loss /= len(test_data)
    accuracy = correct / len(test_data)

    print(f"epochs: {EPOCHS}")
    print(f"final_loss: {test_loss:.6f}")
    print(f"accuracy: {accuracy:.4f}")

if __name__ == "__main__":
    train()
