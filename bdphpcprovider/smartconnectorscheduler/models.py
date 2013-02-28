from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import MultipleObjectsReturned
import logging
import json
import logging.config

from bdphpcprovider.smartconnectorscheduler.errors import InvalidInputError

logger = logging.getLogger(__name__)


class UserProfile(models.Model):
    user = models.ForeignKey(User, unique=True)
    company = models.CharField(max_length=255, blank=True, null=True)
    nickname = models.CharField(max_length=255, blank=True, null=True)

    def __unicode__(self):
        return self.user.username


# declaration of a set of parameter (e.g., XML schema)
class Schema(models.Model):
    """ Representation of a set of parameters (equiv to XML Schema)

        :attribute namespace: namespace for this schema
        :attribute name: unique name
        :attribute description: displayable text describing the schema

    """
    namespace = models.URLField(verify_exists=False, max_length=400)
    description = models.CharField(max_length=80, default="")
    name = models.SlugField(default="", help_text="A unique identifier for the schema")

    class Meta:
        unique_together = (('namespace', 'name'),)

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.namespace)


class ParameterName(models.Model):
    """ A parameter associated with a schema

        :attribute schema: the  :class:`bdphpcprovider.smartconnectorscheduler.models.Schema` which this parameter belongs to
        :attribute name: the name of the parameter
        :attribute type: the type of the parameter from TYPES
        :attribute ranking: int which indicates relative ranking in listings
        :attribute initial: any initial value for this parameter
        :attribute choices: a serialised python list of string choices for the STRLIST type
        :attribute help_text: text that appears in admin tool
        :attribute max_length: maximum length for STRING types
    """
    schema = models.ForeignKey(Schema)
    name = models.CharField(max_length=50)
    # TODO: need to do this so that each paramter can appear only once
    # in each schema

    class Meta:
        unique_together = (('schema', 'name'),)
        ordering = ["-ranking"]

    UNKNOWN = 0
    STRING = 1
    NUMERIC = 2  # only integers
    LINK = 3
    STRLIST = 4
    DATE = 5
    YEAR = 6
    TYPES = (
             (UNKNOWN, 'UNKNOWN'),
             (STRING, 'STRING'),
             (NUMERIC, 'NUMERIC'),
             (LINK, 'LINK'),
             (STRLIST, 'STRLIST'),
             (DATE, 'DATE'),
             (YEAR, 'YEAR')

            )
    # The form used to store dates in the DATE type field
    DATE_FORMAT = "%b %d, %Y"

    type = models.IntegerField(choices=TYPES, default=STRING)

    ranking = models.IntegerField(default=0,
                                  help_text="Describes the relative ordering "
                                  "of parameters when displaying: the larger "
                                  "the number, the more prominent the results")
    initial = models.TextField(default="", blank=True,
                               verbose_name="Initial Value",
                             help_text="The initial value for this parameter")
    choices = models.TextField(default="", blank=True,
                               verbose_name="Choices for the field")
    help_text = models.TextField(default="", blank=True,
                                 verbose_name="Text to help user fill out "
                                              "the field")
    max_length = models.IntegerField(default=255,
                                     verbose_name="Maximum number of "
                                     "characters in a parameter")

    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.schema.name)

    #TODO: make a method to display schema and parameters as XML schema definition
    def get_type_string(self, val):
        for (t, str) in self.TYPES:
            if t == val:
                return str
        return "UNKNOWN"

    def get_value(self, val):
        logger.debug("type=%s" % self.type)
        logger.debug("val=%s" % val)
        res = val
        if self.type == self.NUMERIC:
            try:
                res = int(val)
            except ValueError:
                logger.debug("invalid type")
                raise
        return res


class UserProfileParameterSet(models.Model):
    """ Association of a user profile object with a specific schema.

        :attribute user_profile: the :class:`bdphpcprovider.smartconnectorscheduler.models.MediaObject`
        :attribute schema:  the :class:`bdphpcprovider.smartconnectorscheduler.models.Schema`
        :attribute ranking: int which indicates relative ranking of parameter set in listings
     """
    user_profile = models.ForeignKey(UserProfile, verbose_name="User Profile")
    schema = models.ForeignKey(Schema, verbose_name="Schema")
    #info = models.CharField(max_length=400, null=True)
    ranking = models.IntegerField(default=0)

#    def __unicode__(self):
#        return u'%s (%s)' % (self.user_profile.name, self.schema.name)

    class Meta:
        ordering = ["-ranking"]


class UserProfileParameter(models.Model):
    """ The value for some metadata for a User Profile

        :parameter name: the associated  :class:`bdphpcprovider.smartconnectorscheduler.models.ParameterName` that the value matches to
        :parameter paramset: associated  :class:`bdphpcprovider.smartconnectorscheduler.models.UserProfile` and class:`bdphpcprovider.smartconnectorscheduler.models.Schema` for this value
        :parameter value: the actual value
    """
    name = models.ForeignKey(ParameterName, verbose_name="Parameter Name")
    paramset = models.ForeignKey(UserProfileParameterSet, verbose_name="Parameter Set")
    value = models.TextField(verbose_name="Parameter Value", help_text="The Value of this parameter")
    #ranking = models.IntegerField(default=0,help_text="Describes the relative ordering of parameters when displaying: the larger the number, the more prominent the results")

    def __unicode__(self):
        return u'%s %s %s' % (self.name, self.paramset, self.value)

    def getValue(self,):
        try:
            val = self.name.get_value(self.value)
        except ValueError:
            logger.error("got bad value")
            raise
        return val

    class Meta:
        ordering = ("name",)


def make_stage_transitions(stage, context):
    """ Starting at stage, traverse the whole composite stage and record
    and return the path (assuming no branches).  TODO: branches?
    """
    # FIXME: should be in models.Stage?
    if Stage.objects.filter(parent=stage).count():
        return _make_stage_trans_recur(stage, context, 0)
    else:
        return {'%s' % stage.id: 0}


def _make_stage_trans_recur(stage, context, parent_next_sibling_id):
    # TODO: test this carefully
    logger.debug("mps stage=%s" % stage)
    transition = {}
    childs = Stage.objects.filter(parent=stage).order_by('order')
    logger.debug("childs=%s", childs)
    # FIXME: rewrite this
    for i, child in enumerate(childs):
        key = child.id
        value = childs[i + 1].id if i < len(childs) - 1 else -1
        transition[key] = value
        logger.debug("%s -> %s" % (key, value))
        subtransition = _make_stage_trans_recur(child, context, value)
        logger.debug("subtransiton=%s", subtransition)
        transition.update(subtransition)

    if len(childs) > 0:
        k, v = stage.id, childs[0].id
        logger.debug("%s -> %s" % (key, value))
        transition[k] = v
        k, v = childs.reverse()[0].id, parent_next_sibling_id
        logger.debug("%s -> %s" % (key, value))
        transition[k] = v
    # else:
    #        transition[stage.id] = 0
    logger.debug("transition=%s" % transition)

    return transition

# TODO: if hierarchies become very complicated, may need to use mptt
#from mptt.models import MPTTModel, TreeForeignKey


#class Stage(MPTTModel):
class Stage(models.Model):
    """
    The units of execution.
    """
    name = models.CharField(max_length=256,)
    impl = models.CharField(max_length=256, null=True)
    description = models.TextField(default="")
    order = models.IntegerField(default=0)
    parent = models.ForeignKey('self', null=True, blank=True)
    #parent = TreeForeignKey('self', null=True, blank=True, related_name='children')
    package = models.CharField(max_length=256, default="")

    class MPTTMeta:
        order_insertion_by = ['order']

    def __unicode__(self):
        return u'#%s %s %s %s' % (self.id, self.name, self.description, self.parent)

    def get_next_stage(self, context):
        """
        Given a stage, determine the next stage to execute, by consulting transition map
        """

        transitions = json.loads(context['transitions'])
        logger.debug("transitions=%s" % transitions)
        logger.debug("current_stage=%s" % self)
        logger.debug("self.id=%s" % self.id)
        next_stage_id = transitions["%s" % self.id]
        logger.debug("next_stage_id = %s" % next_stage_id)

        if next_stage_id:
            next_stage = Stage.objects.get(id=next_stage_id)
        else:
            return None
        return next_stage


class Platform(models.Model):
    """
    The envioronment where directives will be executed.
    """
    name = models.CharField(max_length=256)


class Directive(models.Model):
    """
    Holds an platform independent operation provided by an API
    """
    name = models.CharField(max_length=256)


class Command(models.Model):
    """
    Holds a platform specific operation that uses an external API
    Initialised from the specified stage
    """
    directive = models.ForeignKey(Directive)
    stage = models.ForeignKey(Stage, null=True, blank=True)
    platform = models.ForeignKey(Platform)


class DirectiveArgSet(models.Model):
    """
    Describes the argument of a directive.
    The idea is to specify a type for each of the arguments of the directive
    as high level schemas
    which can then be checked against usage.
    """
    directive = models.ForeignKey(Stage)
    order = models.IntegerField()
    schema = models.ForeignKey(Schema)


class SmartConnector(models.Model):
    """
    Pointer to a composite stage that specfies a smart connector
    """
    composite_stage = models.ForeignKey(Stage)


class Context(models.Model):
    """
    Holds a pointer to the currently to be executed stage and all the
    arguments and variable storage for
    that execution
    """
    owner = models.ForeignKey(UserProfile)
    current_stage = models.ForeignKey(Stage)
    CONTEXT_SCHEMA_NS = "tardis.edu.au/schemas/context/schema"

    def get_context(self):
        """
        Returns a readonly dict that holds all the information for the context
        """
        context = {}
        for param in ContextParameter.objects.filter(paramset__context=self):
            context[param.name.name] = param.getValue()
        return context

    def update_context(self, updated_context):
        """
            update the context with new values from a map
        """

        sch = Schema.objects.get(namespace=self.CONTEXT_SCHEMA_NS)
        logger.debug("sch=%s" % sch)
        # FIXME: assumes that each context has only one ContextParameterSet
        try:
            paramset = ContextParameterSet.objects.get(
                schema=sch)
        except ContextParameterSet.DoesNotExist:
            logger.exception("Could not find parameterset for context")
            raise
        except MultipleObjectsReturned:
            logger.exception("Found duplicate entry in ContextParamterSet")
            raise

        logger.debug("paramset=%s" % paramset)
        #TODO: what if entries in original context have been deleted?
        for k, v in updated_context.items():
            logger.debug("k=%s,v=%s" % (k, v))
            try:
                pn = ParameterName.objects.get(schema=sch,
                    name=k)
            except ParameterName.DoesNotExist:
                msg = "Unknown parameter '%s' for context '%s'" % (k, updated_context)
                logger.exception(msg)
                raise InvalidInputError(msg)
            try:
                cp = ContextParameter.objects.get(paramset__context=self,
                    name__name=k, paramset=paramset)
            except ContextParameter.DoesNotExist:
                # TODO: need to check type
                cp = ContextParameter.objects.create(name=pn,
                    paramset=paramset, value=v)
            except MultipleObjectsReturned:
                logger.exception("Found duplicate entry in ContextParamterSet")
                raise
            else:
                # TODO: need to check type
                cp.value = v
                cp.save()


class ContextParameterSet(models.Model):
    """
    All the information required to run the stage in the context
    """
    context = models.ForeignKey(Context)
    schema = models.ForeignKey(Schema, verbose_name="Schema")
    ranking = models.IntegerField(default=0)

    class Meta:
        ordering = ["-ranking"]


class CommandArgument(models.Model):
    """
    A the level of command a representation of a local or remote file or dataset
    NB: unused
    """
    template_url = models.URLField()



class ContextParameter(models.Model):
    name = models.ForeignKey(ParameterName, verbose_name="Parameter Name")
    paramset = models.ForeignKey(ContextParameterSet, verbose_name="Parameter Set")
    value = models.TextField(verbose_name="Parameter Value", help_text="The Value of this parameter")
    #ranking = models.IntegerField(default=0,help_text="Describes the relative ordering of parameters when displaying: the larger the number, the more prominent the results")

    def __unicode__(self):
        return u'%s %s %s' % (self.name, self.paramset, self.value)

    def getValue(self,):
        try:
            val = self.name.get_value(self.value)
        except ValueError:
            logger.error("got bad value")
            raise
        return val

    class Meta:
        ordering = ("name",)


