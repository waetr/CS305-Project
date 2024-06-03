import os
import random
import string

# 文件名
filename = "original.txt"

# 目标文件大小（以KB为单位）
target_size = 100 * 1024 + 1  # 100KB

# 打开文件以写入
with open(filename, "w") as f:
    for _ in range(target_size):
        # 生成一个随机的小写字母
        letter = random.choice(string.ascii_lowercase)
        # 写入文件
        f.write(letter)

print(f"文件 {filename} 已成功创建，大小为 {os.path.getsize(filename)} 字节。")
