awk '{v=$2+0; if (v < 0) v=-v; if (v >= 2.0) print $1}' shear_log.txt | shuf | head -50 | while read f; do
  file="dataset/images/train/$f.jpg"
  [ ! -f "$file" ] && file="dataset/images/val/$f.jpg"
  echo "$f"
  open "$file"
  read -r
done
