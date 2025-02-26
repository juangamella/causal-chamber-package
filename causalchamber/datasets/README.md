You can see what datasets are available at [causalchamber.org](https://causalchamber.org) or by typing:

```Python
datasets.list_available()

# Output:
# Available datasets (last changes on 2024-03-26):
# 
#   lt_camera_walks_v1
#   lt_test_v1
#   wt_intake_impulse_v1
#   lt_malus_v1
#   lt_camera_test_v1
#   wt_test_v1
# 
# Visit https://causalchamber.org for a detailed description of each dataset.
```

For the available experiments in each dataset, you can run:
```python
dataset.available_experiments()

# Output:
# ['palette',
#  'polarizer_effect_bright',
#  'polarizer_effect_dark',
#  'pure_colors_bright',
#  'pure_colors_dark']
```

For the available image sizes (only in image datasets):
```python
experiment.available_sizes()

# Output:
# ['200', '500', 'full']
```
