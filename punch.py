# punch.py #

# Import(s)
import sys, socket, json, threading, time

# Constant(s)
RBUF_SIZE = 11 # size of HB_MESS in bytes
HB_MESS = '~bump~bump~'

class Heartbeat( threading.Thread ):
	udp_socket = None
	net_info = None
	canceled = threading.Event( )
	interval = 0.5
	
	def __init__( self, udp_socket, net_info ):
		threading.Thread.__init__( self )
		self.udp_socket = udp_socket
		self.net_info = net_info

	def run( self ):
		print '\t\tHeartbeat: sending heartbeats...'
		while not self.canceled.is_set( ):
			try:
				bytes_sent = self.udp_socket.sendto( HB_MESS, ( str( self.net_info[ 'pub_ip' ] ), 
										int( self.net_info[ 'pub_port' ] ) ) )
				time.sleep( self.interval )
				if self.canceled.is_set( ): break
				time.sleep( self.interval )
			except BaseException as e:
				print e
		print '\t\tHeartbeat: quiting...'

class Monitor( threading.Thread ):
	udp_socket = None
	canceled = threading.Event( )
	
	def __init__( self, udp_socket ):
		threading.Thread.__init__( self )
		self.udp_socket = udp_socket

	def run( self ):
		print '\tMonitor: listening for heartbeats...'
		while not self.canceled.is_set( ):
			try:
				data, remote_addr = self.udp_socket.recvfrom( RBUF_SIZE )
				print '\tMonitor:[' + str( remote_addr[ 0 ] ) + ':' + str( remote_addr[ 1 ] ) + ']: ' + str( data )
			except socket.timeout:
				pass
			except BaseException as e:
				print e
		print '\tMonitor: quiting...'
		self.udp_socket.close( )

class PunchClient( object ):
	name = None
	rendevous_ip = None
	rendevous_port = 8081
	clients = None
	socket = None
	port = 8085
	ready = False
	running = False
	monitor_thd = None
	heartbeat_thd = None

	def __init__( self, rendevous_ip, name, port ):
		self.rendevous_ip = rendevous_ip
		self.name = name
		self.port = port
		
		try:
			self.socket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
			self.socket.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
			self.socket.settimeout( None )
		except socket.error as e:
			print e
		
		self.ready = True

	def get_netinfo( self ):
		net_info = dict( )

		try:
			net_info.update( { 'name': self.name } )
			net_info.update( { 'priv_ip': self.socket.getsockname( )[ 0 ] } )
			net_info.update( { 'priv_port': self.socket.getsockname( )[ 1 ] } )
		except BaseException as e:
			print e

		return net_info

	def report_netinfo( self ):
		try:
			self.socket.bind( ( '', self.port ) )
			print 'Registering with rendevous server ...'
			self.socket.connect( ( self.rendevous_ip, self.rendevous_port ) )
			self.socket.sendall( 'REPORT:' + json.dumps( self.get_netinfo( ) ) + '\0' )
			self.socket.close( )
		except socket.error as e:
			print e

	def get_data( self ):
		data = ''
		
		while 1:
			try:
				data += self.socket.recv( 1 )
				if data[ -1 ] == '\0':
					return data[ :-1 ]
			except socket.error as e:
				print e

	def get_order( self ):
		order = ''

		while 1:
			order += sys.stdin.read( 1 )
			if order[ -1 ] == '\n':
				order = order[ :-1 ]
				return order

	def print_opts( self ):
		print 'Available commands:'
		print '\tquit - exit application'
		print '\tget - retrieves reported client net infos from rendevous'
		print '\tpunch - prompts for name of client to punch\n'


	def obey_user( self ):
		self.running = True
		print 'Setup complete.'
		self.print_opts( )
	
		while self.running:
			next_order = str( self.get_order( ) )

			if 'quit' in next_order:
				self.running = False

				if not self.heartbeat_thd is None:
					self.heartbeat_thd.canceled.set( )
				if not self.monitor_thd is None:
					self.monitor_thd.canceled.set( )
			
			elif 'get' in next_order:
				self.socket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
				self.socket.settimeout( None )
				self.socket.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
				self.socket.connect( ( self.rendevous_ip, self.rendevous_port ) )
				self.socket.sendall( 'GET:' + '\0' )
				self.clients = json.loads( self.get_data( ) )
				self.socket.close( )
				print self.clients

			elif 'punch' in next_order:

				if self.clients == None:
					print 'Please \'get\' net info from rendevous server first!'
					continue

				print 'Enter name of client to punch: ',
				name = str( self.get_order( ) )

				###
				if self.monitor_thd is None:
					
					# TODO make socket timeout so Monitor can exit nicely
					udp_socket = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
					udp_socket.settimeout( 0.25 )
					udp_socket.bind( ( '', self.port ) )
		
					self.monitor_thd = Monitor( udp_socket )
					self.monitor_thd.start( )
					self.heartbeat_thd = Heartbeat( udp_socket, self.clients[ name ] )
					self.heartbeat_thd.start( )

					# TODO listen for kill, don't kill application: Ctrl-C

			else:
				print 'Unrecognized input! \n'
				self.print_opts( )

# Main
if not len( sys.argv ) == 4:
	print 'Usage:'

else:
	client = PunchClient( str( sys.argv[ 1 ] ), str( sys.argv[ 2 ] ), int( sys.argv[ 3 ]) )
	if client.ready:
		client.report_netinfo( )
		client.obey_user( )
	else:
		print 'PunchClient is not ready, error during initialization'
