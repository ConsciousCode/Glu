'''
File containing base classes and utilities for parsing.
'''

class ParseError(RuntimeError):
	'''
	An error thrown during parsing.
	'''
	def __init__(self,msg,line,col):
		RuntimeError.__init__(self,msg+" (Ln: {}, Col: {})".format(line,col))
		self.line=line
		self.col=col

class ParserBase:
	'''
	Base class for low level parsing.
	'''
	def __init__(self,s):
		self.line=1
		self.col=0
		self.pos=0
		self.text=s
		self.length=len(s)
	
	def space(self):
		'''
		Parse whitespace while keeping track of the line and column.
		'''
		while self.pos<self.length and self.text[self.pos].isspace():
			c=self.text[self.pos]
			if c=='\n':
				self.line+=1
				self.col=0
			elif c=='\r':
				if self.pos+1<self.length and self.text[self.pos+1]=='\n':
					self.pos+=1
				self.line+=1
				self.col=0
			else:
				self.col+=1
			self.pos+=1
	
	def maybe(self,c):
		'''
		Try to parse the given character and increment on success.
		
		Returns true if the character was encountered.
		'''
		if self.pos<self.length and self.text[self.pos]==c:
			self.pos+=1
			self.col+=1
			return True
		return False