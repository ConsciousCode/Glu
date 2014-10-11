import code

left=False
right=True

class ValueNode:
	'''
	AST node representing a value.
	'''
	def __init__(self,tok,val):
		self.tok=tok
		self.val=val
	
	def __repr__(self):
		return repr(self.val)
	
	def build(self,context):
		#reuse constant nodes to conserve memory
		try:
			return context.consts[self.val]
		except KeyError:
			node=code.number(self.val)
			context.consts[self.val]=node
			return node

class IdentNode:
	def __init__(self,tok):
		self.tok=tok
	
	def __repr__(self):
		return "%{}".format(self.tok.text)
	
	def build(self,context):
		return context.vars[self.tok.text]

class OperatorNode:
	'''
	AST node representing an operator.
	'''
	def __init__(self,tok,code,args):
		self.tok=tok
		self.code=code
		self.args=args
	
	def __repr__(self):
		#return "({} {})".format(self.code,self.args)
		return "({} {})".format(
			self.code,' '.join(repr(x) for x in self.args)
		)
	
	def build(self,context):
		return code.do(self.code,[arg.build(context) for arg in self.args])

class ReturnNode:
	def __init__(self,tok,val):
		self.tok=tok
		self.val=val
	
	def __repr__(self):
		return "(return {})".format(self.val)
	
	def build(self,context):
		return code.ret(self.val.build(context))

class GotoNode:
	'''
	AST node representing a goto statement.
	'''
	def __init__(self,tok,label):
		self.tok=tok
		self.label=label
	
	def __repr__(self):
		return "(goto {})".format(self.label.text)
	
	def build(self,context):
		try:
			next=context.labels[self.label.text]
		except KeyError:
			next=code.FixNode()
			try:
				context.fix[self.label.text].append(next)
			except KeyError:
				context.fix[self.label.text]=[next]
		context.block=context.block.add(code.goto(next))
		return None

class LabelNode:
	'''
	AST node representing a label statement.
	'''
	def __init__(self,tok,label):
		self.tok=tok
		self.label=label
	
	def __repr__(self):
		return "(label {})".format(self.label.text)
	
	def build(self,context):
		block=context.block
		next=code.block()
		block.add(code.goto(next))
		context.block=next
		try:
			for fix in context.fix[self.label.text]:
				fix.replace(next)
		except KeyError:pass
		return None

class CallNode:
	'''
	A function call.
	'''
	def __init__(self,func,args):
		def get_args(x):
			if x.tok==",":
				return [x.args[0]]+get_args(x.args[1])
			return [x]
		
		self.tok=func
		self.args=get_args(args)
	
	def __repr__(self):
		return "(call {} {{{}}})".format(
			self.tok,', '.join(repr(x) for x in self.args)
		)
	
	def build(self,context):
		return code.do("call",[arg.build(context) for arg in self.args])

class IfNode:
	'''
	An if statement.
	'''
	def __init__(self,func,cond,then):
		self.tok=func
		self.cond=cond
		self.then=then
	
	def __repr__(self):
		if self.body:
			return "if({}){}".format(self.cond,self.body)
		return "if({})".format(self.cond,self.body)
	
	def build(self,context):
		cond=self.cond.build(context)
		then=self.then.build(context)
		context.block=context.block.add(code.ifnot(cond,then))
		
		return None

class BlockNode:
	def __init__(self,ast):
		self.ast=ast
	
	def __repr__(self):
		return "{{{}}}".format(' '.join(repr(x) for x in self.ast))
	
	def build(self,context):
		block=code.block()
		for expr in self.ast:
			x=expr.build(context)
			if x is not None:
				block.add(x)
		return block

class AssignNode:
	def __init__(self,name,val):
		self.name=name
		self.val=val
	
	def __repr__(self):
		return "({} = {})".format(self.name,self.val)
	
	def build(self,context):
		context.vars[self.name.tok.text]=self.val.build(context)
		
		return None

class DeclNode(AssignNode):
	def __init__(self,type,name,val):
		AssignNode.__init__(self,name,val)
		self.type=type
	
	def __repr__(self):
		return "({} {} = {})".format(self.type,self.name,self.val)

class Context:
	def __init__(self,parser):
		self.vars={} #name:graph node
		self.labels={} #name:graph node -> known labels
		self.fix={} #name:[graph node] -> goto nodes to unknown labels
		self.consts={} #val:const node
		self.block=code.block()
		self.entry=self.block

class AST(list):
	def flatten(self,parser,context):
		for expr in self:
			x=expr.build(context)
			if x is not None:
				context.block.add(x)
		return context.entry
	
	def build(self,parser):
		return code.Code(self.flatten(parser,Context(parser)))
	
	def copy(self):
		return AST(list.copy(self))

class Opstack:
	def __init__(self,stack=None):
		self.stack=stack or []
	
	def __len__(self):
		return len(self.stack)
	
	def __repr__(self):
		return repr(self.stack)
	
	def push(self,op,ast):
		if op.args==2:
			def wcond(a,b):
				return (a.args==1 and a.priority>b.priority) or (
					a.priority>b.priority or (
						a.assoc==left and a.priority==b.priority
					)
				)
			while len(self.stack) and wcond(self.peek(),op):
				self.pop(ast)
		
		self.stack.append(op)
	
	def pop(self,scope):
		self.stack.pop().apply(scope)
	
	def peek(self):
		if len(self.stack):
			return self.stack[-1]
		return None
	
	def copy(self):
		return Opstack(self.stack.copy())