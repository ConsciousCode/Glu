import parsebase as pb
import string

IDENT_STARTCHARS=string.ascii_letters+"$_";
IDENT_CHARS=IDENT_STARTCHARS+string.digits

binary={"+","-","*","/","="}
miscops={"(",")",";","{","}"}

class Token:
	'''
	Base class for tokens.
	'''
	def __init__(self,text,line,col):
		self.text=text
		self.line=line
		self.col=col
	
	def __repr__(self):
		return self.text
	
	def __eq__(self,x):
		return self.text==x
	
	def __ne__(self,x):
		return self.text!=x

class ValueToken(Token):
	'''
	Base class for value tokens (numbers, strings, etc)
	'''
	pass

class NumberToken(ValueToken):
	'''
	A token representing any number constant.
	'''
	def __init__(self,text,dot,line,col):
		ValueToken.__init__(self,text,line,col)
		if dot:
			self.val=float(text)
		else:
			self.val=int(text)

class IdentToken(ValueToken):
	'''
	A token representing an identifer.
	'''
	pass

class OperatorToken(Token):
	'''
	A token representing any operator.
	'''
	pass

class CommentToken(Token):
	'''
	A token representing a comment (single or multi-lined)
	'''
	def __init__(self,data,line,col):
		def stringify(x):
			if type(x) is str:
				return x
			return "#("+''.join(stringify(e) for e in x)+")#"
		
		Token.__init__(self,stringify(data),line,col)
		
		self.data=data
	
	def __repr__(self):
		return self.text

class Tokenizer(pb.ParserBase):
	def __init__(self,s):
		pb.ParserBase.__init__(self,s)
	
	def parse_literal(self,set):
		x=self.pos
		tok=None
		
		while self.pos<len(self.text):
			t=self.text[x:self.pos+1]
			if t in set:
				tok=t
				self.pos+=1
			else:
				break
		
		if tok:
			self.col+=self.pos-x
			return tok
		
		return None
	
	def parse_number(self):
		'''
		Attempt to parse and return the next number token, else return None.
		'''
		dot=False
		x=self.pos
		col=self.col
		
		while self.pos<self.length:
			c=self.text[self.pos]
			if c.isdigit():pass
			elif c=='.' and not dot:
				dot=True
			else:
				break
			self.pos+=1
		
		num=self.text[x:self.pos]
		if num:
			self.col+=self.pos-x
			return NumberToken(num,dot,self.line,col)
		
		return None
	
	def parse_op(self):
		'''
		Attempt to parse and return the next operator token, else return None.
		'''
		col=self.col
		
		op=self.parse_literal(binary)
		if op:
			return OperatorToken(op,self.line,col)
		
		op=self.parse_literal(miscops)
		if op:
			return OperatorToken(op,self.line,col)
		
		return None
	
	def parse_ident(self):
		'''
		Attempt to parse and return the next identifier, else return None.
		'''
		col=self.col
		
		if self.pos>=self.length:
			return None
		
		x=self.pos
		
		if self.text[self.pos] not in IDENT_STARTCHARS:
			return None
		
		self.pos+=1
		
		while self.pos<self.length and self.text[self.pos] in IDENT_CHARS:
			self.pos+=1
		
		ident=self.text[x:self.pos]
		if ident:
			self.col+=self.pos-x
			return IdentToken(ident,self.line,col)
		
		return None
	
	def parse_comment(self):
		'''
		Attempt to parse and return the next comment, else return None.
		'''
		
		def parse_mlcomment_internals(self):
			data=[]
			x=self.pos
			col=self.col-2
			line=self.line
			
			while self.pos<self.length:
				c=self.text[self.pos]
				if c=="#":
					self.pos+=1
					if self.pos<self.length:
						if self.text[self.pos]=="(":
							data.append(self.text[x:self.pos])
							data.append(parse_mlcomment_internals(self))
							x=self.pos
					else:
						break
				elif c==")":
					self.pos+=1
					if self.pos<self.length:
						if self.text[self.pos]=="#":
							self.pos+=1
							return CommentToken(data,line,col)
					else:
						break
				self.pos+=1
			
			raise pb.ParseError("Unterminated multiline comment",line,col)
		
		if self.pos>=self.length:
			return None
		
		if self.text[self.pos]!="#":
			return None
		
		self.pos+=1
		
		if self.text[self.pos]=="(":
			self.pos+=1
			
			return parse_mlcomment_internals(self)
		else:
			col=self.col
			x=self.pos
			while self.pos<self.length:
				if self.text[self.pos] in "\r\n":
					break
				self.pos+=1
			
			self.col+=self.pos-x
			return CommentToken(self.text[x:self.pos],self.line,col)
	
	def next(self):
		'''
		Attempt to parse and return the next token, else return None.
		'''
		if self.pos>=self.length:
			return None
		
		self.space()
		
		#Comment tokens shouldn't even reach the AST builder, loop until
		# the next token isn't a comment.
		tok=True
		while tok:
			tok=self.parse_number()
			if tok:
				return tok
			
			tok=self.parse_op()
			if tok:
				return tok
			
			tok=self.parse_ident()
			if tok:
				return tok
			
			tok=self.parse_comment()
		
		if self.pos<len(self.text):
			raise pb.ParseError(
				"Unrecognized character '{}'".format(self.text[self.pos]),
				self.line,self.col
			)
		return None
	
	def hasNext(self):
		return self.pos<self.length