# Copyright (C) 2013, RMIT University

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import logging

from bdphpcprovider.smartconnectorscheduler.smartconnector import Stage
from bdphpcprovider.smartconnectorscheduler.hrmcstages import clear_temp_files, \
    get_filesys, get_settings, get_run_info
from bdphpcprovider.smartconnectorscheduler.botocloudconnector import create_environ
from bdphpcprovider.smartconnectorscheduler import smartconnector
from bdphpcprovider.smartconnectorscheduler import hrmcstages

logger = logging.getLogger(__name__)


class Create(Stage):

    def __init__(self, user_settings=None):
        self.user_settings = user_settings.copy()
        self.group_id = ''
        self.platform = None
        self.boto_settings = user_settings.copy()

    def triggered(self, run_settings):
        """
            Return True if there is a platform
            but not group_id
        """
        #logger.debug("User_settings %s \n Run_settings %s" % (self.user_settings, run_settings))

        '''
        if smartconnector.key_exists(run_settings,
            'http://rmit.edu.au/schemas/stages/create/group_id'):
            try:
                self.platform = smartconnector.get_existing_key(run_settings,
                 'http://rmit.edu.au/schemas/system/platform')
            except KeyError:
                return False
            else:
                return True
        return False
        '''

        if self._exists(run_settings,
            'http://rmit.edu.au/schemas/stages/configure',
            'configure_done'):
            if not self._exists(run_settings,
                'http://rmit.edu.au/schemas/stages/create', 'group_id'):
                if self._exists(run_settings,
                    'http://rmit.edu.au/schemas/system', 'platform'):
                    self.platform = run_settings['http://rmit.edu.au/schemas/system'][u'platform']
                    return True
        return False

    def process(self, run_settings):
        """
        Make new VMS and store group_id
        """
        #self.boto_settings.update(run_settings)
        number_vm_instances = run_settings['http://rmit.edu.au/schemas/hrmc'][u'number_vm_instances']
        logger.debug("VM instance %d" % number_vm_instances)

        smartconnector.copy_settings(self.boto_settings, run_settings,
            'http://rmit.edu.au/schemas/system/platform')
        smartconnector.copy_settings(self.boto_settings, run_settings,
            'http://rmit.edu.au/schemas/stages/create/vm_image')
        smartconnector.copy_settings(self.boto_settings, run_settings,
            'http://rmit.edu.au/schemas/stages/create/vm_size')
        smartconnector.copy_settings(self.boto_settings, run_settings,
            'http://rmit.edu.au/schemas/stages/create/security_group')
        smartconnector.copy_settings(self.boto_settings, run_settings,
            'http://rmit.edu.au/schemas/stages/create/group_id_dir')
        smartconnector.copy_settings(self.boto_settings, run_settings,
            'http://rmit.edu.au/schemas/stages/create/custom_prompt')
        smartconnector.copy_settings(self.boto_settings, run_settings,
            'http://rmit.edu.au/schemas/stages/create/cloud_sleep_interval')
        smartconnector.copy_settings(self.boto_settings, run_settings,
            'http://rmit.edu.au/schemas/stages/create/nectar_username')
        smartconnector.copy_settings(self.boto_settings, run_settings,
            'http://rmit.edu.au/schemas/stages/create/nectar_password')

        self.boto_settings['username'] = run_settings['http://rmit.edu.au/schemas/stages/create']['nectar_username']
        self.boto_settings['password'] = run_settings['http://rmit.edu.au/schemas/stages/create']['nectar_password']
        self.boto_settings['username'] = 'root'  # FIXME: schema value is ignored

        key_file = hrmcstages.retrieve_private_key(self.boto_settings, self.user_settings['nectar_private_key'])
        self.boto_settings['private_key'] = key_file
        self.boto_settings['nectar_private_key'] = key_file

        logger.debug("botosettings=%s" % self.boto_settings)
        self.group_id = create_environ(number_vm_instances, self.boto_settings)
        if not self.group_id:
            self.group_id = ''  # FIXME: do we we mean '' or None here?
            logger.debug("No new VM instance can be created for this computation. Retry later.")
            #clear_temp_files(run_settings)
            #sys.exit()

    def output(self, run_settings):
        """
        Inserting a new group if into run settings.
        """

        run_settings.setdefault(
            'http://rmit.edu.au/schemas/stages/create', {})[u'group_id'] \
            = self.group_id
        logger.debug("Updated run settings %s" % run_settings)
        return run_settings
