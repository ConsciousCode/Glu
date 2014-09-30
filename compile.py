import cpy3compile

def compile(asm,target="cpy3"):
	if target is "cpy3":
		return cpy3compile.compile(asm)
	
	raise NotImplementedError()