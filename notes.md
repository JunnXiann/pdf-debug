## PDF Transformation Matrix

In PDF, transformation matrices are represented as [a b c d e f], which corresponds to:

```
| a  b  0 |
| c  d  0 |
| e  f  1 |
```

For a pure rotation matrix by angle θ, we would expect:
```
| cos(θ)  sin(θ)  0 |
| -sin(θ) cos(θ)  0 |
| 0       0       1 |
```

So a = cos(θ), b = sin(θ), c = -sin(θ), and d = cos(θ).

## Why `arctan2(b, a)` works

The code calculates the angle using:
```python
angle = np.degrees(np.arctan2(b, a))
```