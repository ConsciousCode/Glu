import struct

noret={
	"goto",
	"return",
	"nop",
	"ifnot"
}

unary=[
	"goto",
	"return",
	"neg",
	"alias"
]

binary=[
	"ifnot",
	"add",
	"sub",
	"mul",
	"div"
]

variadic=[
	"phi"
]

opname=["nop"]+unary+binary+variadic

opmap={opname[x]:x for x in range(len(opname))}

class CodeError(RuntimeError):
	'''
	Error raised while processing Glu assembly code.
	'''
	pass

class Label:
	'''
	A representation of a label used in the constant table. This corresponds
	to the "ref code" type.
	'''
	def __init__(self,pc):
		self.pc=pc
	
	def __repr__(self):
		return "#{}".format(self.pc)
	
	def __eq__(self,other):
		try:
			return self.pc==other.pc
		except AttributeError:
			return False

class Opcode:
	'''
	A single opcode.
	'''
	def __init__(self,reg,code,args):
		self.reg=reg
		if type(code) is int:
			self.op=opname[code]
			self.code=code
		else:
			self.op=code
			self.code=opmap[code]
		self.args=args
	
	def __repr__(self):
		if self.reg:
			return "(%{} = {} {})".format(
				self.reg,self.op,' '.join("%{}".format(x) for x in self.args)
			)
		return "({} {})".format(
			self.op,' '.join("%{}".format(x) for x in self.args)
		)

class GraphNode:
	def __init__(self,dep):
		self.use=[]
		self.dep=dep

class ConstNode(GraphNode):
	def __init__(self,reg,vars,consts):
		GraphNode.__init__(self,[])
		self.reg=reg
	
	def __repr__(self):
		return "<var {}>".format(self.reg)
	
	def visit(self,visitor):
		return visitor.visit_const(self)

class OpNode(GraphNode):
	'''
	Used to piece together the control flow graph.
	'''
	def __init__(self,op,vars,consts):
		self.op=op
		
		if op.reg and op.reg<=len(consts):
			raise CodeError(
				"Output register overlaps with constant register"
			)
		
		dep=[]
		for arg in op.args:
			a=vars[arg]
			a.use.append(self)
			dep.append(a)
		
		GraphNode.__init__(self,dep)
	
	def __repr__(self):
		return repr(self.op)
	
	def visit(self,visitor):
		return visitor.visit_op(self)

class Code:
	def __init__(self,code,consts):
		self.consts=consts
		self.code=code
		
		#Find all labels
		labels=[]
		for c in self.consts:
			if isinstance(c,Label):
				labels.append(c.pc)
		self.labels=labels
		
		#Build the graph vars structure
		vars={}
		for x in range(len(consts)):
			vars[x+1]=ConstNode(x+1,vars,consts)
		
		self.aliases={}
		ops=[]
		for op in code:
			if op.op=="alias":
				self.alias[op.args[0]]=op.args[1]
			else:
				gn=OpNode(op,vars,consts)
				ops.append(gn)
				if op.reg:
					vars[op.reg]=gn
		
		#Load the graph in a meaningful way
		sg=[]
		for gn in ops:
			if len(gn.use)==0 and type(gn.op) is not int:
				sg.append(gn)
		
		self.graph=sg
	
	def __repr__(self):
		lines=[]
		if len(self.consts):
			lines.append(".data")
			x=0
			for c in self.consts:
				lines.append("\t${} = {}".format(x,c))
				x+=1
		
		def format_arg(x):
			if x<=len(self.consts):
				const=self.consts[x-1]
				if type(const) is Label:
					return repr(const)
				return "${}".format(x-1)
			return "%{}".format(x-1)
		
		if len(self.code):
			lines.append(".code")
			for pc in range(len(self.code)):
				c=self.code[pc]
				
				if Label(pc) in self.consts:
					lines.append("#{}:".format(pc))
				
				args=[]
				for arg in c.args:
					args.append(format_arg(arg))
				
				if c.reg:
					lines.append("\t%{} = {} {}".format(
						c.reg-1,c.op,' '.join(args)
					))
				else:
					lines.append("\t{} {}".format(c.op,' '.join(args)))
		
		return "\n".join(lines)
	
	'''
	def serialize(self):
		def pack(x):
			if isinstance(x,int):
				bl=x.bit_length()
				size=bl//8+bool(bl%8)
				return b"Ni"+struct.pack("<H",size)+
					x.to_bytes(size,"little")
			if isinstance(x,float):
				return b"Nf"+struct.pack("<d",x)
			if isinstance(x,complex):
				if x.imag.is_integer():
					return b"Nci"
		
		return struct.pack("<H",len(self.consts))+[
	'''