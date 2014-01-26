from django.conf import settings
import copy

class ScaffoldReport(object):
    """ Base class for any actual scaffold reports
    A scaffold report is named after UI effects for moving 
    various filters and previews into the report
    building screen. All reports require customized 
    options set by the programmer.
    """
    name = ""
    name_verbose = None
    model = None
    preview_fields = ['last_name', 'first_name']
    num_preview = 3
    filters = []

    def __init__(self):
        self._possible_filters = [] # developer selected filters from subclass
        self._active_filters = [] # end user selected filters from view
        self.report_context = {}
        self.filter_errors = []
        self.add_fields = []
        field_names = []
        for possible_filter in self.filters:
            if possible_filter.get_name() in field_names:
                raise Exception(
                    'Duplicate field names in scaffold report. Please set a different name for {}.'.format(possible_filter.get_name()))
            field_names += [possible_filter.get_name()]
            self._possible_filters += [possible_filter]

    @property
    def get_name(self):
        if self.name_verbose != None:
            return self.name_verbose
        return self.name.replace('_', ' ')
    
    def handle_post_data(self, data):
        for filter_data in data:
            for possible_filter in self._possible_filters:
                if possible_filter.__class__.__name__ == filter_data['name']:
                    filter_instance = copy.copy(possible_filter)
                    filter_instance.build_form()
                    filter_instance.raw_form_data = filter_data.get('form', None)
                    self._active_filters += [filter_instance]

    def get_queryset(self):
        """ Return a queryset of the model
        filtering any active filters
        """
        report_context = {}
        queryset = self.model.objects.all()
        for active_filter in self._active_filters:
            queryset = active_filter.process_filter(queryset, report_context)
            if active_filter.form.errors:
                self.filter_errors += [{
                    'filter': active_filter.form.data['filter_number'],
                    'errors': active_filter.form.errors,
                }]
            else:
                report_context = active_filter.get_report_context(report_context)
                self.add_fields += active_filter.add_fields
        self.report_context = dict(self.report_context.items() + report_context.items())
        return queryset

    def get_appy_context(self):
        """ Return a context dict for use in an appy template
        Acts a like context in Django template rendering.
        """
        appy_context = {}
        appy_context['objects'] = self.get_queryset()
        return appy_context

    def report_to_list(self, user, preview=False):
        """ Convert to python list """
        queryset = self.get_queryset()
        if preview:
            queryset = queryset[:self.num_preview]

        if self.preview_fields:
            preview_fields = self.preview_fields
        else:
            preview_fields = ['__unicode__']

        result_list = []
        for obj in queryset:
            result_row = []
            for field in preview_fields:
                field = self.get_field_name(field)
                print field
                cell = getattr(obj, field)
                if callable(cell):
                    cell = cell()
                result_row += [cell]
            for field in self.add_fields:
                cell = getattr(obj, field)
                if callable(cell):
                    cell = cell()
                result_row += [cell]
                
            result_list += [result_row]
        return result_list
    
    def get_field_verbose(self, field):
        if isinstance(field, tuple) and len(field) == 2:
            field = field[1]
        return field
    
    def get_field_name(self, field):
        if isinstance(field, tuple) and len(field) == 2:
            field = field[0]
        return field
        

    def get_preview_fields(self):
        if self.preview_fields:
            preview_fields = []
            all_preview_fields = self.preview_fields + self.add_fields
            for field in all_preview_fields:
                field = self.get_field_verbose(field)
                try:
                    preview_fields += [self.model._meta.get_field_by_name(field)[0].verbose_name.title()]
                except:
                    preview_fields += [field.replace('_', ' ')]
            return preview_fields
        else:
            return [self.model._meta.verbose_name_plural.title()]


try:
    from collections import OrderedDict
except:
    OrderedDict = dict # pyflakes:ignore

def autodiscover():
    """
    Auto-discover INSTALLED_APPS report.py modules and fail silently when
    not present. Borrowed form django.contrib.admin
    """
    from django.utils.importlib import import_module
    from django.utils.module_loading import module_has_submodule

    global scaffold_reports

    for app in settings.INSTALLED_APPS:
        mod = import_module(app)
        try:
            before_import_registry = copy.copy(scaffold_reports)
            import_module('%s.scaffold_reports' % app)
        except:
            scaffold_eports = before_import_registry
            if module_has_submodule(mod, 'scaffold_reports'):
                raise

class ScaffoldReportClassManager(object):
    """
    Class to handle registered reports class. 
    Borrowed from django-model-report Thanks!
    """
    _register = OrderedDict()

    def __init__(self):
        self._register = OrderedDict()

    def register(self, slug, rclass):
        if slug in self._register:
            raise ValueError('Slug already exists: %s' % slug)
        setattr(rclass, 'slug', slug)
        self._register[slug] = rclass

    def get_report(self, slug):
        # return class
        return self._register.get(slug, None)

    def get_reports(self):
        # return clasess
        return self._register.values()


scaffold_reports = ScaffoldReportClassManager()
