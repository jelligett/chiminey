# Copyright (C) 2014, RMIT University

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


from bdphpcprovider.smartconnectorscheduler import models

RMIT_SCHEMA = "http://rmit.edu.au/schemas"
SWEEP_SCHEMA = RMIT_SCHEMA + "/input/sweep"
logger = logging.getLogger(__name__)


class CoreDirective():
    def define_rand_number_sweep(self):
        subdirective = models.Directive.objects.get(
            name="randomnumber"
        )
        sweep_stage, _ = models.Stage.objects.get_or_create(name="sweep_rand",
            description="Sweep for Random",
            package="bdphpcprovider.examples.randomnumbers.randsweep.RandSweep",
            order=100)
        sweep_stage.update_settings({
            u'http://rmit.edu.au/schemas/stages/sweep':
            {
                u'directive': subdirective.name
            }
            })
        sweep, _ = models.Directive.objects.get_or_create(name="sweep_rand",
            description="Rand Sweep Connector",
            stage=sweep_stage)

        RMIT_SCHEMA = "http://rmit.edu.au/schemas"
        for i, sch in enumerate([
                RMIT_SCHEMA + "/input/system/compplatform",
                RMIT_SCHEMA + "/input/system",
                RMIT_SCHEMA + "/input/mytardis",
                RMIT_SCHEMA + "/input/sweep",
                ]):
            schema = models.Schema.objects.get(namespace=sch)
            das, _ = models.DirectiveArgSet.objects.get_or_create(
                  directive=sweep, order=i, schema=schema)

    def define_parent_stage(self):
        parent = "bdphpcprovider.smartconnectorscheduler.stages.composite.ParallelStage"
        parent_stage, _ = models.Stage.objects.get_or_create(
            name="random_number_connector",
            description="Random number parent",
            package=parent,
            order=0)
        return parent_stage
        
        
    def define_create_stage(self):
        create_package = "bdphpcprovider.corestages.create.Create"
        create_stage, _ = models.Stage.objects.get_or_create(name="create",
            description="This is the core create stage",
            parent=self.define_parent_stage(),
            package=create_package,
            order=1)
        create_stage.update_settings({u'http://rmit.edu.au/schemas/stages/create':
                {
                    u'vm_size': "m1.small",
                    u'vm_image': "ami-0000000d",
                    u'cloud_sleep_interval': 20,
                    u'security_group': '["ssh"]',
                    u'group_id_dir': 'group_id',
                    u'custom_prompt': '[smart-connector_prompt]$',
                    u'nectar_username': 'root',
                    u'nectar_password': ''
                }})
        return create_stage

    def define_configure_stage(self):
        configure_package = "bdphpcprovider.corestages.configure.Configure"
        configure_stage, _ = models.Stage.objects.get_or_create\
            (name="configure",
            description="This is the core configure stage",
            parent=self.define_parent_stage(),
            package=configure_package,
            order=0)
        configure_stage.update_settings({
            u'http://rmit.edu.au/schemas/system':
                {
                    u'random_numbers': 'file://127.0.0.1/randomnums.txt'
                },
        })
        return configure_stage

    def define_bootstrap_stage(self):
        bootstrap_package = "bdphpcprovider.corestages.bootstrap.Bootstrap"
        bootstrap_stage, _ = models.Stage.objects.get_or_create(
            name="bootstrap",
            description="This is bootstrap stage of this smart connector",
            parent=self.define_parent_stage(),
            package=bootstrap_package,
            order=20)
        bootstrap_stage.update_settings(
            {
                u'http://rmit.edu.au/schemas/stages/setup':
                    {
                        u'payload_source': '',
                        u'payload_destination': '',
                        u'payload_name': '',
                        u'filename_for_PIDs': 'PIDs_collections',
                    },
            })
        return bootstrap_stage

    def define_schedule_stage(self):
        schedule_package = "bdphpcprovider.corestages.schedule.Schedule"
        schedule_stage, _ = models.Stage.objects.get_or_create(
            name="schedule",
            description="This is schedule stage of this smart connector",
            parent=self.define_parent_stage(),
            package=schedule_package,
            order=25)
        return schedule_stage

    def define_execute_stage(self):
        execute_package = "bdphpcprovider.corestages.execute.Execute"
        execute_stage, _ = models.Stage.objects.get_or_create(name="execute",
            description="This is a core execute stage",
            parent=self.define_parent_stage(),
            package=execute_package,
            order=30)
        execute_stage.update_settings(
            {
            u'http://rmit.edu.au/schemas/stages/run':
                {
                    u'payload_cloud_dirname': '',
                    u'compile_file': '',
                    u'retry_attempts': 1,
                },
            })

    def define_wait_stage(self):
        wait_package = "bdphpcprovider.corestages.wait.Wait"
        wait_stage, _ = models.Stage.objects.get_or_create(
            name="wait",
            description="This is core wait stage",
            parent=self.define_parent_stage(),
            package=wait_package,
            order=40)
        wait_stage.update_settings({
            u'http://rmit.edu.au/schemas/stages/wait':
                {
                    u'synchronous': 1
                },
        })
        return wait_stage

    def define_destroy_stage(self):
        destroy_package = "bdphpcprovider.corestages.destroy.Destroy"
        destroy_stage, _ = models.Stage.objects.get_or_create(
            name="destroy",
            description="This is core destroy stage",
            parent=self.define_parent_stage(),
            package=destroy_package,
            order=70)
        destroy_stage.update_settings({})
        return destroy_stage

    def define_directive(self, directive_name, subdirective_name='', description='', hidden=False):
        parent_stage = self.assemble_stages()
        new_directive, _ = models.Directive.objects.get_or_create(
            name=directive_name,
            defaults={'stage': parent_stage,
                      'description': description,
                      'hidden': hidden}
        )
        if subdirective_name:
            new_subdirective = self.define_subdirective(new_directive, subdirective_name)
            self.create_ui(new_subdirective)
        else:
            self.create_ui(new_directive)

    def define_subdirective(self, directive, subdirective_name):
        subdirective = models.Directive.objects.get(name=subdirective_name)
        max_order = 0
        for das in models.DirectiveArgSet.objects.filter(directive=subdirective):
            new_das = models.DirectiveArgSet.objects.create(
                directive=directive, order=das.order, schema=das.schema)
            max_order = max(max_order, das.order)

        schema = models.Schema.objects.get(namespace=SWEEP_SCHEMA)
        new_das = models.DirectiveArgSet.objects.create(
            directive=directive, order=max_order + 1, schema=schema)
        return subdirective

    def define_sweep_stage(self, subdirective_name):
        sweep_stage, _ = models.Stage.objects.get_or_create(name="sweep_%s" % subdirective_name,
            description="Sweep for %s" % subdirective_name,
            package="bdphpcprovider.corestages.sweep.Sweep",
            order=100)
        sweep_stage.update_settings({
            u'http://rmit.edu.au/schemas/stages/sweep':
            {
                u'directive': subdirective_name
            }
            })
        return sweep_stage

    def create_ui(self, new_directive):
        pass

    def assemble_stages(self):
        parent_stage = self.define_parent_stage()
        self.define_configure_stage()
        self.define_create_stage()
        self.define_bootstrap_stage()
        self.define_schedule_stage()
        self.define_execute_stage()
        self.define_wait_stage()
        self.define_destroy_stage()
        return parent_stage






