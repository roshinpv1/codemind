
import cocoindex.targets
print("Available targets:", dir(cocoindex.targets))
try:
    print("LanceDB target:", cocoindex.targets.LanceDB)
except AttributeError:
    print("LanceDB target NOT found in cocoindex.targets")
