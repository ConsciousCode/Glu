import cpy3compile
import snowcompile

def compile(asm,target="cpy3"):
	if target=="cpy3":
		return cpy3compile.compile(asm)
	elif target=="snow":
		return snowcompile.compile(asm)
	
	raise NotImplementedError()