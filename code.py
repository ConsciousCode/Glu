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

class Opcode:
	def __init__(self,reg,code,args):
		if isinstance(reg,str):
			raise CodeError("Opcode parameters are (reg,code,args)")
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

class Memo:
	def __init__(self):
		self.memo=[]
	
	def has(self,x):
		return x in self.memo
	
	def id(self,x):
		try:
			return self.memo.index(x)
		except ValueError:
			self.memo.append(x)
			return len(self.memo)-1

class GraphNode:
	def __init__(self):
		self.use=[]

class FixNode(GraphNode):
	'''
	Acts as a placeholder node until the real one is encountered. This is
	mostly used with control nodes.
	'''
	
	def __repr__(self,memo=None):
		if memo is not None:
			return "!{}".format(memo.id(self))
		return "!!"
	
	def replace(self,node):
		for use in self.use:
			use.replace(self,node)
			node.use.append(use)
	
	def visit(self,visitor,data=None):
		raise CodeError(
			"Unreplaced fix node being visited in control flow graph"
		)

class OpNode(GraphNode):
	def __init__(self,op,args):
		GraphNode.__init__(self)
		
		if type(op) is int:
			self.op=code.opname[op]
		else:
			self.op=op
		self.args=args
		for arg in args:
			arg.use.append(self)
	
	def __repr__(self,memo=None):
		if memo:
			if memo.has(self):
				return "%{}".format(memo.id(self))
			
			if len(self.use)>2:
				return "(%{} = {} {})".format(
					memo.id(self),self.op,' '.join(
						x.__repr__(self) for x in self.args
					)
				)
		else:
			memo=Memo()
		
		return "({} {})".format(
			self.op,' '.join(x.__repr__(memo) for x in self.args)
		)
	
	def visit(self,visitor,data=None):
		return visitor.visit_op(self,data)

class NumberNode(GraphNode):
	def __init__(self,val):
		GraphNode.__init__(self)
		
		self.val=val
	
	def __repr__(self,memo=None):
		return repr(self.val)
	
	def visit(self,visitor,data=None):
		return visitor.visit_number(self,data)

class ControlNode(GraphNode):
	def __init__(self,block):
		GraphNode.__init__(self)
		
		self.block=block
		block.use.append(self)
	
	def replace(self,old,new):
		if self.block==old:
			self.block=new

class ReturnNode(ControlNode):
	def __repr__(self,memo=None):
		return "(return {})".format(self.block.__repr__(memo))
	
	def visit(self,visitor,data=None):
		return visitor.visit_return(self,data)

class GotoNode(ControlNode):
	def __repr__(self,memo=None):
		return "(goto {})".format(self.block.__repr__(memo))
	
	def visit(self,visitor,data=None):
		return visitor.visit_goto(self,data)

class IfNode(ControlNode):
	def __init__(self,cond,block):
		ControlNode.__init__(self,block)
		
		self.cond=cond
		cond.use.append(self)
	
	def __repr__(self,memo=None):
		return "(if {} {})".format(
			self.cond.__repr__(memo),
			self.block.__repr__(memo)
		)
	
	def visit(self,visitor,data=None):
		return visitor.visit_if(self,data)
	
	def replace(self,old,new):
		ControlNode.__init__(self,old,new)
		if self.cond==old:
			self.cond=new

class BlockNode(GraphNode):
	def __init__(self):
		GraphNode.__init__(self)
		
		self.nodes=[]
		self.next=None
	
	def __repr__(self,memo=None):
		def tabulate(x):
			if x:
				return "\t"+x.replace("\n","\n\t")
			return x
		
		def stringify(self,memo):
			content=self.nodes
			if self.next is not None:
				content=content+[self.next]
			
			if len(content):
				return "{{\n{}\n}}".format(
					tabulate('\n'.join(x.__repr__(memo) for x in content))
				)
			return "{}"
		
		if memo:
			if memo.has(self):
				return "#{}".format(memo.id(self))
			
			if len(self.use)>1:
				return "#{}: {}".format(memo.id(self),stringify(self,memo))
			return stringify(self,memo)
		
		return stringify(self,Memo())
	
	def visit(self,visitor,data=None):
		return visitor.visit_block(self,data)
	
	def add(self,node):
		if isinstance(node,ControlNode):
			self.next=node
			return BlockNode()
		else:
			self.nodes.append(node)
			return self

def number(val):
	if not isinstance(val,(int,float)):
		raise TypeError("codegen.number(val) takes a number type.")
	return NumberNode(val)

def do(op,args):
	if not isinstance(args,list):
		args=[args]
	
	if op=="goto":
		return GotoNode(args[0])
	return OpNode(op,args)

def ret(val):
	return ReturnNode(val)

def goto(block):
	return GotoNode(block)

def ifnot(cond,block):
	return IfNode(cond,block)

def block():
	return BlockNode()

class Code:
	def __init__(self,entry):
		self.entry=entry
	
	def __repr__(self):
		return repr(self.entry)