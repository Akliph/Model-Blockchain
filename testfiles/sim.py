"""
This is the file used to layout the supply control timeline. Change the user defined variables and run to see all
of the dependent variables in the supply control timeline.
"""
from sys import argv

"""
User defined variables (These parameters are the ones used by the nodes by default)
"""

decimal_places = 2
starting_reward = 1000
split = 1000
average_blocktime = 1800

"""
Variable Declarations
"""

total = 0
era = 0
current_reward = starting_reward

"""
Run through timeline
"""

while current_reward != 10**-decimal_places:
    total += current_reward * split
    era += 1
    print(f"Split: {era} | Reward: {format(current_reward, f'.{decimal_places}f')} "
          f"| Total Supply: {format(total, f'.{decimal_places}f')}")
    current_reward = round(current_reward / 2, decimal_places)

total += current_reward * split
era += 1

"""
Print result
"""

print(f"Split: {era} | Reward: {format(current_reward, f'.{decimal_places}f')} | Total Supply: {total}")
current_reward = round(current_reward / 2, decimal_places)

print("")

print("[Independent variables...]")
print(f"Smallest denomination of the coin: {10**-decimal_places} | Starting reward: {starting_reward} | "
      f"Block reward is split every {split} blocks")
print(f"Each block takes about {average_blocktime} seconds, or {average_blocktime / 60} minutes to mine")

print("")

print("[Dependent variables...]")
print(f"The total supply of the coin: {total}")
print(f"It will take {era} splits to get to the total supply")
print(f"The entire supply of coins will be mined in about {era * split * average_blocktime} seconds | "
      f"{(era * split * average_blocktime) / 60} minutes | {(era * split * average_blocktime) / 60 / 60} hours | "
      f"{(era * split * average_blocktime)/ 60 / 60/ 24} days | "
      f"{(era * split * average_blocktime) / 60 / 60 / 24 / 365} years")
print(f"A single split will happen about every {(average_blocktime * split) / 60 / 60 / 24} days | "
      f"{(average_blocktime * split) / 60/ 60 / 24/ 365} years")
