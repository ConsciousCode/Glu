import code
import struct
import dis
from collections import deque

def f():pass

func=type(f)
pyco=type(f.__code__)

def pyop(x):
	return struct.pack('b',dis.opmap[x])

def pyarg(x):
	return struct.pack("H",x)

def unary(x):
	x=pyop(x)
	def op_build(c,op,pypc):
		pypc,a=c.visit(op.args[0],pypc)
		return pypc+1,a+[x]
	
	return op_build

def binary(x):
	x=pyop(x)
	def op_build(c,op,pypc):
		pypc,a=c.visit(op.args[0],pypc)
		pypc,b=c.visit(op.args[1],pypc)
		return pypc+1,a+b+[x]
	
	return op_build

pyconv={
	"nop":(lambda c,op,pypc:[]),
	"neg":unary("UNARY_NEGATIVE"),
	"add":binary("BINARY_ADD"),
	"sub":binary("BINARY_SUBTRACT"),
	"mul":binary("BINARY_MULTIPLY"),
	"div":binary("BINARY_TRUE_DIVIDE")
}

class CompileError(RuntimeError):
	def __init__(self,msg,pc):
		RuntimeError.__init__(self,"{} (Code {})".format(msg,pc))
		self.pc=pc

class Compiler:
	def __init__(self):
		self.vars=[]
		self.asm=None
		self.nlocals=0
		self.stacksize=0
		self.labels={} #id(block node):pypc
		self.consts=[]
	
	def jump(self,label,c,pypc):
		label=self.asm.consts[label.reg-1].pc
		try:
			c[c.index(None)]=pyarg(self.labels[label])
			return c
		except KeyError:pass
		
		fix=pypc+c.index(None)
		
		try:
			self.fix[label].append(fix)
		except KeyError:
			self.fix[label]=[fix]
		
		#None will be replaced later, but should fail nicely if it isn't
		return pypc+len(b''.join(b"!!" if x is None else x for x in c)),c
	
	def visit_number(self,num,pypc):
		try:
			x=self.consts.index(num.val)
		except ValueError:
			self.consts.append(num.val)
			x=len(self.consts)-1
		return pypc+3,[pyop("LOAD_CONST"),pyarg(x)]
	
	def visit_op(self,opn,pypc):
		pypc,out=pyconv[opn.op](self,opn,pypc)
		
		return pypc,out
	
	def visit_block(self,block,pypc):
		try:
			return pypc+3,[pyop("JUMP_ABSOLUTE"),pyarg(self.labels[id(block)])]
		except KeyError:pass
		
		#Record the PC for later jumps, which must occur if len(block.use) > 1
		if len(block.use)>1:
			self.labels[id(block)]=pypc
		
		c=[]
		for gn in block.nodes:
			pypc,tc=self.visit(gn,pypc)
			c.extend(tc)
		
		pypc,tc=self.visit(block.next,pypc)
		
		return pypc,c+tc
	
	def visit_return(self,ret,pypc):
		pypc,val=self.visit(ret.block,pypc)
		return pypc+1,val+[pyop("RETURN_VALUE")]
	
	def visit_goto(self,goto,pypc):
		return self.visit(goto.block,pypc)
	
	def visit_if(self,ifnot,pypc):
		block_pypc,cond=self.visit(ifnot.cond,pypc)
		pypc,block=self.visit(ifnot.block,block_pypc)
		
		return pypc,cond+[pyop("POP_JUMP_IF_FALSE"),pyarg(block_pypc)]+block
	
	def visit(self,gn,pypc):
		if gn is None:
			return []
		
		return gn.visit(self,pypc)
	
	def compile(self,asm):
		self.asm=asm
		
		_,c=self.visit(asm.entry,0)
		
		return func(pyco(
			#argcount,kwonlyargcount,nlocals,stacksize,flags,codestring
			0,0,self.nlocals,self.stacksize,0,b''.join(c),
			#consts,names,varnames,filename,name,firstlineno,lnotab
			tuple(self.consts),(),(),"<glu>","glufunc",1,b''
		),{},"glufunc")

def compile(asm):
	return Compiler().compile(asm)