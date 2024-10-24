import { initializeCalendar } from './calendar.js';
import { initializeColorManager } from './colorManager.js';
import { initializeMyTeam } from './my_team.js';
import { initializeNotes } from './notes.js';
import { initializeSchedule } from './schedule.js';
import { initializeTeamManagement, updateCallSequenceNumbers } from './team_management.js';
import { initializeTimeOff } from './timeoff.js';
import { initializeUserManagement } from './user_management.js';
import { initializeAuth } from './auth.js';
import { showNotification, showDeleteConfirmationModal } from './utils.js';
import { initializeSelectAll, initializeTableSearch } from './table_utils.js';
import { initializeFlatpickr } from './form_utils.js';

document.addEventListener('DOMContentLoaded', function() {
    initializeAuth();
    initializeCalendar();
    initializeColorManager();
    initializeMyTeam();
    initializeNotes();
    initializeSchedule();
    initializeTeamManagement();
    initializeTimeOff();
    initializeUserManagement();
    initializeSelectAll('selectAll', 'schedule_ids[]', 'batchDeleteBtn');
    initializeTableSearch('userSearch', 'userTableBody');
    initializeTableSearch('teamSearch', 'teamTableBody');
    initializeTableSearch('roleSearch', 'roleTableBody');
    initializeTableSearch('timeoffSearch', 'timeoffTableBody');
    initializeTableSearch('scheduleSearch', 'scheduleTableBody');
    initializeFlatpickr();
    
    // Make utility functions globally available
    window.showNotification = showNotification;
    window.showDeleteConfirmationModal = showDeleteConfirmationModal;
    window.updateCallSequenceNumbers = updateCallSequenceNumbers;
});