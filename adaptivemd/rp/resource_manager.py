import radical.pilot as rp
import radical.utils as ru
import os
from exceptions import *

class ResourceManager(object):

    """
    A resource manager takes the responsibility of placing resource requests on different, possibly multiple,
    DCIs. Currently, the runtime system being used is RADICAL Pilot and hence the resource request is made via
    Pilot Jobs.

    :arguments: 
        :resource_desc: dictionary with details of the resource request + access credentials of the user 
            :example: resource_desc = {  'resource': 'xsede.stampede', 'walltime': 120, 'cores': 64, 'project: 'TG-abcxyz'}
        :database_url: link to the MongoDB to be used for RADICAL Pilot purposes

    """


    def __init__(self, resource_desc, database_url=None):


        self._uid = ru.generate_id('resource_manager.rp')
        self._logger = ru.get_logger('resource_manager.rp')

        if not database_url:
            self._mlab_url = database_url


        self._mlab_url = os.environ.get('RADICAL_PILOT_DBURL',None)
        if not self._mlab_url:
            raise Error(text='RADICAL_PILOT_DBURL not defined. Please assign a valid mlab url')

        self._session       = None    
        self._pmgr          = None
        self._pilot         = None
        self._resource      = None
        self._walltime      = None
        self._cores         = None
        self._project       = None
        self._access_schema = None
        self._queue         = None


        if self._validate_resource_desc(resource_desc):
            self._populate(resource_desc)
        else:            
            raise Error(msg='Resource description incorrect')
        

    # ------------------------------------------------------------------------------------------------------------------
    # Getter methods
    # ------------------------------------------------------------------------------------------------------------------

    @property
    def pilot(self):

        """
        :getter: Return reference to the submitted Pilot
        """
        return self._pilot

    @property
    def session(self):

        """
        :getter: Return reference to the Radical Pilot session instance currently being used
        """
        return self._session

    @property
    def pmgr(self):

        """
        :getter: Return reference to the Radical Pilot manager currently being used
        """
        return self._pmgr

    @property
    def resource(self):

        """
        :getter: Return user specified resource name
        """
        return self._resource

    @property
    def walltime(self):

        """
        :getter: Return user specified walltime
        """
        return self._walltime

    @property
    def cores(self):

        """
        :getter: Return user specified number of cores
        """
        return self._cores

    @property
    def project(self):

        """
        :getter: Return user specified project ID
        """
        return self._project

    @property
    def access_schema(self):

        """
        :getter: Return user specified access schema -- 'ssh' or 'gsissh' or None
        """
        return self._access_schema

    @property
    def queue(self):

        """
        :getter: Return user specified resource queue to be used
        """
        return self._queue
    

    # ------------------------------------------------------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------------------------------------------------------

    def _validate_resource_desc(self, resource_desc):

        """
        **Purpose**: Validate the resource description that was provided to ResourceManager

        :arguments: dictionary consisting of details of the resource request
        :return: boolean (valid/invalid)
        """

        try:

            if not isinstance(resource_desc, dict):
                raise TypeError(expected_type=dict, actual_type=type(resource_desc))


            expected_keys = [   'resource',
                                'walltime',
                                'cores',
                                'project'
                            ]

            for key in expected_keys:
                if key not in resource_desc:
                    raise MissingError(obj='resource description', missing_attribut=key)

            if not isinstance(resource_desc['resource'],str):
                raise TypeError(expected_type=str, actual_type=type(resource_desc['resource']))

            if not isinstance(resource_desc['walltime'], int):
                raise TypeError(expected_type=int, actual_type=type(resource_desc['walltime']))

            if not isinstance(resource_desc['cores'], int):
                raise TypeError(expected_type=int, actual_type=type(resource_desc['cores']))

            if not isinstance(resource_desc['project'],str):
                raise TypeError(expected_type=str, actual_type=type(resource_desc['project']))            

            if 'access_schema' in resource_desc:
                if not isinstance(resource_desc['access_schema'], str):
                    raise TypeError(expected_type=str, actual_type=type(resource_desc['access_schema']))

            if 'queue' in resource_desc:
                if not isinstance(resource_desc['queue'], str):
                    raise TypeError(expected_type=str, actual_type=type(resource_desc['queue']))

            return True

        except Exception, ex:
            raise Error(msg='Failed to validate resource description, error: %s'%ex)



    def _populate(self, resource_desc):

        """
        **Purpose**: Populate the ResourceManager attributes with values provided in the resource description

        :arguments: valid dictionary consisting of details of the resource request
        """

        try:

            self._resource = resource_desc['resource']
            self._walltime = resource_desc['walltime']
            self._cores = resource_desc['cores']
            self._project = resource_desc['project']

            if 'access_schema' in resource_desc:
                self._access_schema = resource_desc['access_schema']

            if 'queue' in resource_desc:
                self._queue = resource_desc['queue']


            self._logger.info('Resource manager population successful')

        except Exception, ex:
            self._logger.error('Resource manager population unsuccessful')
            raise Error(msg='Resource manager population unsuccessful')



    # ------------------------------------------------------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------------------------------------------------------

    def submit_resource_request(self):

        """
        **Purpose**: Function to initiate the resource request.

        Details: Currently, submits a Pilot job using the RADICAL Pilot runtime system.
        """

        try:

            def _pilot_state_cb(pilot, state):
                self._logger.info('Pilot %s state: %s'%(pilot.uid, state))

                if state == rp.FAILED:
                    self._logger.error('Pilot has failed')

            self._session = rp.Session(dburl=self._mlab_url)

            self._pmgr = rp.PilotManager(session=self._session)
            self._pmgr.register_callback(_pilot_state_cb)

            pd_init = {
                    'resource'  : self._resource,
                    'runtime'   : self._walltime,
                    'cores'     : self._cores,
                    'project'   : self._project,
                    }
    
            if self._access_schema:
                pd_init['access_schema'] = self._access_schema
    
            if self._queue:
                pd_init['queue'] = self._queue
    

            # Create Compute Pilot with validated resource description
            pdesc = rp.ComputePilotDescription(pd_init)
   
            # Launch the pilot
            self._pilot = self._pmgr.submit_pilots(pdesc)

            self._logger.info('Resource request submission successful.. waiting for pilot to go Active')
    
            # Wait for pilot to go active
            self._pilot.wait([rp.ACTIVE, rp.FAILED])

            if self._pilot.state == rp.FAILED:
                raise Exception

            self._logger.info('Pilot is now active')

            return self._pilot

        except KeyboardInterrupt:

            if self._session:
                self._session.close()

            self._logger.error('Execution interrupted by user (you probably hit Ctrl+C), '+
                                            'trying to exit callback thread gracefully...')
            raise KeyboardInterrupt

        except Exception, ex:
            self._logger.error('Resource request submission failed')
            raise Error(msg='Resource request submission failed')



    def cancel_resource_request(self):

        """
        **Purpose**: Cancel the resource request
        """

        try:

            self._pilot.cancel()
            self._session.close(cleanup=False)

        except KeyboardInterrupt:

            self._logger.error('Execution interrupted by user (you probably hit Ctrl+C), '+
                                            'trying to exit callback thread gracefully...')
            raise KeyboardInterrupt

        except Exception, ex:
            self._logger.error('Could not cancel resource request, error: %s'%ex)
            raise Error(msg='Could not cancel resource request, error: %s'%ex)

    # ------------------------------------------------------------------------------------------------------------------