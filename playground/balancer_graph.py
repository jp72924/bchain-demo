import matplotlib.pyplot as plt
import numpy as np

# Parameters
MAX_SUPPLY = 10**8  # 100 million
n = 100  # Example input for static graphs
iterations = 20  # For dynamic simulation

# === Static Analysis (k vs Values) ===
k_values = np.arange(0, 6)
burn_rates = n * (2/9)**k_values
coin_rates = burn_rates * (1 - (1/3)**(k_values + 1))
net_burn_rates = burn_rates - coin_rates

plt.figure(figsize=(12, 6))
plt.plot(k_values, burn_rates, 'bo-', label='BURN_RATE')
plt.plot(k_values, coin_rates, 'go-', label='COIN_RATE')
plt.plot(k_values, net_burn_rates, 'ro-', label='NET_BURN_RATE')
plt.title('Value Decay with Recursion Depth (k)\n(n=100)')
plt.xlabel('Recursion Depth (k)')
plt.ylabel('Value')
plt.xticks(k_values)
plt.legend()
plt.grid(True)
plt.show()

# === Dynamic Simulation (Supply Over Time) ===
supply_history = []
k_history = []
total_supply = MAX_SUPPLY
recursion_limit = 0

for i in range(iterations):
    # Calculate rates
    burn_rate = total_supply * (2/9)**recursion_limit
    coin_rate = burn_rate * (1 - (1/3)**(recursion_limit + 1))
    net_burn = burn_rate - coin_rate
    
    # Update supply and track
    total_supply -= net_burn
    supply_history.append(total_supply)
    k_history.append(recursion_limit)
    
    # Update recursion depth
    if total_supply < MAX_SUPPLY / (2 ** (recursion_limit + 1)):
        recursion_limit += 1

# Plot supply over time
plt.figure(figsize=(12, 6))
plt.plot(supply_history, 'm^-', markersize=8)
plt.title('Total Supply Evolution Over Iterations')
plt.xlabel('Iteration')
plt.ylabel('Total Supply')
plt.grid(True)
plt.show()

# Plot recursion depth changes
plt.figure(figsize=(12, 6))
plt.step(range(iterations), k_history, 'g-s', where='post')
plt.title('Recursion Depth (k) Adjustment')
plt.xlabel('Iteration')
plt.ylabel('Recursion Depth (k)')
plt.yticks(range(max(k_history)+1))
plt.grid(True)
plt.show()