from .market.wizards import *
from .setting.wizards import *
from .shared.wizards import *
from .project.wizards import *
from .organization.wizards import *

__all__ = [ 'kafka_config_wizard','system_type_config_wizard','kafka_cron_manager_wizard','task_assignment_wizard', 'task_mapping_wizard', 'contractor_representative_wizard']
__all__ = __all__ + ['create_remote_requirement_wizard']