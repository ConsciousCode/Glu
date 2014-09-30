import code
import struct
import dis
from collections import deque

def f():pass

func=type(f)
pyco=type(f.__code__)

def op(x):
	return struct.pack('b',dis.opmap[x])

def unary(x):
	x=op(x)
	def op_build(c,r,d):
		return c.visit(d[0])+[x]
	
	return op_build

def binary(x):
	x=op(x)
	def op_build(c,r,d):
		return c.visit(d[0])+c.visit(d[1])+[x]
	
	return op_build

pyconv={
	"nop":(lambda c,r,d:None),
	"goto":(lambda c,r,d:c.jump(d[0],[op("JUMP_ABSOLUTE"),None])),
	"ifnot":(lambda c,r,d:c.jump(
		d[1],c.visit(d[0])+[op("POP_JUMP_IF_FALSE"),None])
	),
	"return":unary("RETURN_VALUE"),
	"neg":unary("UNARY_NEGATIVE"),
	"add":binary("BINARY_ADD"),
	"sub":binary("BINARY_SUBTRACT"),
	"mul":binary("BINARY_MULTIPLY"),
	"div":binary("BINARY_TRUE_DIVIDE")
}

pyarity={
	"nop":0,
	"goto":0,
	"neg":0,
	"add":-1,
	"sub":-1,
	"mul":-1,
	"div":-1,
	"return":-1
}

class CompileError(RuntimeError):
	def __init__(self,msg,pc):
		RuntimeError.__init__(self,"{} (Code {})".format(msg,pc))
		self.pc=pc

def arg(x):
	return struct.pack("H",x)

class Compiler:
	def __init__(self):
		self.vars=[]
		self.asm=None
		self.nlocals=0
		self.stacksize=0
		self.labels={}
		self.fix={}
		self.pypc=0
		self.pc=0
	
	def jump(self,label,c):
		label=self.asm.consts[label.reg-1].pc
		try:
			c=c.copy()
			c[c.index(None)]=arg(self.labels[label])
			return c
		except KeyError:pass
		
		pypc=self.pypc+c.index(None)
		
		try:
			self.fix[label].append(pypc)
		except KeyError:
			self.fix[label]=[pypc]
		
		#None will be replaced later, but should fail nicely if it isn't
		return c
	
	def visit_const(self,const):
		return [op("LOAD_CONST"),arg(const.reg-1)]
	
	def visit_op(self,opn):
		out=pyconv[opn.op.op](self,opn.op.reg,opn.dep)
		
		if len(opn.use)>1:
			out+=[op("DUP_TOP")]*(len(opn.use)-1)
		
		#Only occurs once when this is the label to fix to
		if self.pc in self.asm.labels:
			self.labels[self.pc]=self.pypc
		
		self.pypc+=len(b''.join(b'  ' if x is None else x for x in out))
		self.pc+=1
		
		return out
	
	def visit(self,gn):
		if gn is None:
			return []
		
		return gn.visit(self)
		
		out=pyconv[gn.op.op](self,gn.op.reg,gn.dep)
		
		if len(gn.use)>1:
			out+=[op("DUP_TOP")]*(len(gn.use)-1)
		
		#Only occurs once when this is the label to fix to
		if self.pc in self.asm.labels:
			self.labels[self.pc]=self.pypc
		
		self.pypc+=len(b''.join(b'  ' if x is None else x for x in out))
		self.pc+=1
		
		return out
	
	def compile(self,asm):
		self.asm=asm
		
		c=[]
		for gn in asm.graph:
			c.extend(self.visit(gn))
		
		#Go back and fix gotos with labels defined after their use
		for label,pypcs in self.fix.items():
			for pypc in pypcs:
				c[pypc]=struct.pack("H",self.labels[label])
		
		return func(pyco(
			#argcount,kwonlyargcount,nlocals,stacksize,flags,codestring
			0,0,self.nlocals,self.stacksize,0,b''.join(c),
			#consts,names,varnames,filename,name,firstlineno,lnotab
			tuple(asm.consts),(),(),"<glu>","glufunc",1,b''
		),{},"glufunc")

def compile(asm):
	return Compiler().compile(asm)