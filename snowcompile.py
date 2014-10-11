import code

def stringify_const(x):
	if isinstance(x,(int,float)):
		return "{{number {}}}".format(x)
	elif isinstance(x,(code.Label)):
		return "{{label {}}}".format(x.pc)
	else:
		raise RuntimeError("Unknown constant type {}".format(type(x)))

def build_data(asm):
	data='\n\t'.join(
		"\n\t\t{{const {}}}".format(stringify_const(x)) for x in asm.consts
	)
	if data:
		return data+"\n\t"
	return ""

def build_op(op):
	args=' '.join(repr(x) for x in op.args)
	if args:
		return "{{op {} {} {}}}".format(op.op,op.reg,args)
	return "{{op {} {}}}".format(op.op,op.reg)

def build_code(asm):
	c='\n\t\t'.join(build_op(x) for x in asm.code)
	if c:
		return "\n\t\t"+c
	return ""

def compile(asm):
	return "{{gluasm\n\t{}\n\t{}\n}}".format(
		"{{data {}}}".format(build_data(asm)),
		"{{code {}\n\t}}".format(build_code(asm))
	)