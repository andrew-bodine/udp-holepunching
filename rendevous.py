# Andrew C. Bodine & Daniel S. Lavine
# UDP Hole Punching Rendevous Server

# Import(s)
import socket, sys, json

class Rendevous( object ):
	clients = None		# Maintains a dictionary of reported client net information
	doorbell = None		# Rendevous server's doorbell socket
	ready = False		# Indicates Rendevous server initialization status
	port = 8081		# Port that Rendevous server listens for connections on

	def __init__( self ):

		self.clients = dict( )

		try: 
			self.doorbell = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
			self.doorbell.settimeout( None )
			self.doorbell.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
		except socket.error as e:
			print e
			return

		self.ready = True

	def serve( self ):
		
		self.doorbell.bind( ( '', self.port ) )
		self.doorbell.listen( 5 )
		print 'Rendevous server listening for connections @ ' + str( self.doorbell.getsockname( ) )

		while 1:
			conn, r_addr = self.doorbell.accept( )
			self.handle_conn( conn, r_addr )

	def handle_conn( self, conn, r_addr ):
		
		print 'Connection established from ' + str( r_addr )
		data = self.get_data( conn )
		print '\tRECV: ' + data

		if 'REPORT:' in data:
			# Store client net info
			data = json.loads( str( data.split( 'REPORT:' )[ 1 ] ) )
			net_info = dict( data ) 
			net_info.update( { 'pub_ip': str( r_addr[ 0 ] ), 'pub_port': str( r_addr[ 1 ] ) } )
			del net_info[ 'name' ]
			self.clients.update( { data[ 'name' ]: net_info } )	# Stores: { name: { priv_ip: some_ip, priv_port: some_port } }
		
		elif 'GET:' in data:
			# Return all reported client net info
			conn.sendall( json.dumps( self.clients ) + '\0' )
	
	def get_data( self, conn ):
		data = ''

		while 1:
			data += conn.recv( 1 )

			if data[ -1 ] == '\0':
				data = data[ :-1 ]
				return str( data ) 

# Main
rendevous = Rendevous( )

if rendevous.ready:
	rendevous.serve( )
else:
	print 'Rendevous server isn\'t up, error during initialization'
