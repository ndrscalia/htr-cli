import cv2
import sys

bucket = sys.argv[1] if len(sys.argv) > 1 else "1_2"

lines = []
with open("shear_log.txt") as f:
    for line in f:
        name, val = line.strip().rsplit(" ", 1)
        v = abs(float(val))
        if bucket == "0_1" and 0 <= v < 1.0:
            lines.append((name, float(val)))
        elif bucket == "1_2" and 1.0 <= v <= 2.1:
            lines.append((name, float(val)))

print(f"Found {len(lines)} images in bucket '{bucket}'")
print("Press any key for next, 'q' to quit\n")

for name, val in lines:
    path = f"dataset/images/train/{name}.jpg"
    img = cv2.imread(path)
    if img is None:
        path = f"dataset/images/val/{name}.jpg"
        img = cv2.imread(path)
    if img is None:
        print(f"Not found: {name}")
        continue

    cv2.setWindowTitle("shear check", f"{name}  shear={val}")
    cv2.imshow("shear check", img)
    key = cv2.waitKey(0)
    if key == ord("q"):
        break

cv2.destroyAllWindows()
