import re

fail_pattern = re.compile(".*FAIL|.*[Ee]rror")
line = "Measurement qrror \"trise\" fAIL'ed"
print(line)
print(fail_pattern.match(line))
print(fail_pattern.match(line) is not None)
print(line.find("FAIL"))

