import code

ops={
	"nop":(lambda a,c:None),
	"goto":(lambda a,c:c.goto(a[0])),
	"ifnot":(lambda a,c:c.goto(a[0]) if not a else None),
	"add":(lambda a,c:a[0]+a[1]),
	"sub":(lambda a,c:a[0]-a[1]),
	"mul":(lambda a,c:a[0]*a[1]),
	"div":(lambda a,c:a[0]/a[1]),
	"return":(lambda a,c:c.ret(a[0]))
}

class InterpretError(RuntimeError):
	def __init__(self,msg,pc):
		RuntimeError.__init__(self,"{} (Code {})".format(msg,pc))
		self.pc=pc

class Context:
	def __init__(self,asm):
		self.vars={}
		for x in range(len(asm.consts)):
			self.vars[x+1]=asm.consts[x]
		self.pc=0
		self.retval=None
	
	def get(self,id):
		if id==0:
			return None
		return self.vars[id]
	
	def set(self,id,val):
		if id==0:
			return val
		
		if id in self.vars:
			raise InterpretError(
				"Attempted to reassign var {}".format(id),self.pc
			)
		self.vars[id]=val
		return val
	
	def goto(self,label):
		self.pc=label.pc-1
	
	def next(self):
		self.pc+=1
	
	def ret(self,x):
		self.retval=x

def interpret(asm):
	ctx=Context(asm)
	while ctx.pc<len(asm.code) and ctx.retval is None:
		op=asm.code[ctx.pc]
		ctx.set(op.reg,ops[op.op]([ctx.get(x) for x in op.args],ctx))
		ctx.next()
	
	return ctx.retval