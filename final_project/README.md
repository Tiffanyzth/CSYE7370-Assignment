# Instruction
Modify config.py：
```python
python main.py
```

# Result
```python
if config.do_predict:
	result = trainer.generate('丽日照残春')
	print("".join(result))
	result = trainer.gen_acrostic('深度学习')
	print("".join(result))
	
丽日照残春，
风光摇落时。
不知花发意，
不得见春风。

深山高下有余灵，万里无人见钓矶。
度日茱萸人不得，一枝不得不相见。
学舞一枝花落叶，不知何处是君王。
习书不见金闺后，应是君王赐手间。
```

# Reference
> https://github.com/chenyuntc/pytorch-book<br>