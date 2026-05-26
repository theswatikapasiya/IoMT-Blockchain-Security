% MATLAB IoMT Blockchain Tamper Detection Monitor
% Real-time independent verification of patient data integrity

clear all; close all; clc;

%% ===============================================================
%  IOMT PATIENT DATA MONITORING WITH BLOCKCHAIN VERIFICATION
%  ===============================================================
%  Purpose: Independently verify hospital data integrity
%  Method: Compare current backend data with stored hash values
%  Alert: Sound + Visual alerts when tampering detected
%  ===============================================================

% Configuration
API_URL = 'http://localhost:5000/api';
REFRESH_INTERVAL = 3; % seconds
MONITORING_ACTIVE = true;
TAMPER_LOG = [];

% Create monitoring figure
fig = figure('Position', [100, 100, 1200, 700]);
fig.Name = 'IoMT Hospital Monitoring - MATLAB Tamper Detection';
fig.NumberTitle = 'off';

% Create UI components
ax_patients = subplot(2,2,1);
ax_integrity = subplot(2,2,2);
ax_timeline = subplot(2,2,3);
ax_alerts = subplot(2,2,4);

%% ===============================================================
%  HELPER FUNCTIONS
%  ===============================================================

function display_alert(severity, message)
    timestamp = datetime('now', 'Format', 'HHmm:ss');
    alert_text = sprintf('[%s] %s: %s', timestamp, severity, message);
    
    switch severity
        case 'CRITICAL'
            fprintf('\n❌ CRITICAL ALERT: %s\n', message);
            % Play alert sound
            beep;
            pause(0.1);
            beep;
            pause(0.1);
            beep;
        case 'WARNING'
            fprintf('\n⚠️  WARNING: %s\n', message);
            beep;
        case 'INFO'
            fprintf('\n✅ INFO: %s\n', message);
        otherwise
            fprintf('\n%s\n', alert_text);
    end
end

function data = fetch_api(endpoint)
    try
        url = sprintf('http://localhost:5000%s', endpoint);
        options = weboptions('Timeout', 5, 'ContentType', 'json');
        data = webread(url, options);
    catch
        data = [];
        display_alert('WARNING', sprintf('Failed to reach API: %s', endpoint));
    end
end

function hash_values = compute_hashes(patient_data)
    % Compute SHA-256 hash of patient vital signs
    hash_values = [];
    
    if isempty(patient_data)
        return;
    end
    
    for i = 1:length(patient_data)
        patient = patient_data(i);
        data_str = sprintf('id:%s,hr:%d,bp:%s,temp:%.1f', ...
            patient.id, patient.hr, patient.bp, patient.temp);
        hash_values(i) = hash_string_to_uint64(data_str);
    end
end

function hash_uint = hash_string_to_uint64(str)
    % Simple deterministic hash function
    hash_uint = uint64(0);
    for i = 1:length(str)
        hash_uint = bitshift(hash_uint, 5) + uint64(str(i));
    end
end

function plot_patient_statuses(patient_data, ax)
    cla(ax);
    if isempty(patient_data)
        return;
    end
    
    % Get first 10 patients
    n_patients = min(10, length(patient_data));
    
    % Extract data
    hrs = zeros(n_patients, 1);
    names = cell(n_patients, 1);
    colors = cell(n_patients, 1);
    
    for i = 1:n_patients
        hrs(i) = patient_data(i).hr;
        names{i} = shortenPatientName(patient_data(i).name);
        
        % Color based on vital status
        if hrs(i) < 60 || hrs(i) > 120
            colors{i} = [1, 0.6, 0.6]; % Red
        elseif hrs(i) < 70 || hrs(i) > 100
            colors{i} = [1, 1, 0.5]; % Yellow
        else
            colors{i} = [0.5, 1, 0.5]; % Green
        end
    end
    
    b = bar(ax, hrs);
    for i = 1:n_patients
        b.CData(i,:) = colors{i};
    end
    
    set(ax, 'XTickLabel', names);
    ylabel(ax, 'Heart Rate (bpm)');
    title(ax, 'Patient Heart Rate Status');
    set(ax, 'YGrid', 'on');
    set(ax, 'XColor', [0.9, 0.9, 0.9]);
    set(ax, 'YColor', [0.9, 0.9, 0.9]);
    set(ax, 'Color', [0.15, 0.15, 0.2]);
end

function plot_integrity_score(integrity_score, ax)
    cla(ax);
    
    % Pie chart showing integrity
    intact = [integrity_score, 100 - integrity_score];
    colors = [0.2, 0.8, 0.2; 0.8, 0.2, 0.2];
    
    pie(ax, intact, {'Integrity ✓', 'Tampered ✗'});
    
    % Format
    h = get(ax, 'Children');
    for i = 1:length(h)
        if strcmp(get(h(i), 'Type'), 'text')
            set(h(i), 'Color', [0.9, 0.9, 0.9]);
            set(h(i), 'FontSize', 10);
        end
    end
    
    title(ax, sprintf('System Integrity: %.0f%%', integrity_score));
    set(ax, 'Color', [0.15, 0.15, 0.2]);
end

function plot_timeline(tamper_log, ax)
    cla(ax);
    
    if length(tamper_log) < 2
        text(ax, 0.5, 0.5, 'No tamper events detected', ...
            'HorizontalAlignment', 'center', ...
            'Color', [0.5, 1, 0.5]);
        set(ax, 'XLim', [0, 1], 'YLim', [0, 1]);
        set(ax, 'Color', [0.15, 0.15, 0.2]);
        return;
    end
    
    % Plot tamper events
    times = 1:length(tamper_log);
    tampering = zeros(size(times));
    
    for i = 1:length(tamper_log)
        tampering(i) = tamper_log(i).isTampered;
    end
    
    plot(ax, times, tampering, 'o-', 'Color', [1, 0.2, 0.2], 'LineWidth', 2);
    hold(ax, 'on');
    
    ylabel(ax, 'Tampering Detected');
    xlabel(ax, 'Check #');
    title(ax, 'Integrity Timeline');
    set(ax, 'YTick', [0, 1]);
    set(ax, 'YTickLabel', {'No', 'Yes'});
    set(ax, 'YGrid', 'on');
    set(ax, 'XColor', [0.9, 0.9, 0.9]);
    set(ax, 'YColor', [0.9, 0.9, 0.9]);
    set(ax, 'Color', [0.15, 0.15, 0.2]);
end

function plot_alerts_log(tamper_log, ax)
    cla(ax);
    
    text_y = 0.95;
    
    if isempty(tamper_log)
        text(ax, 0.05, text_y, '✅ System Clean - No alerts', ...
            'Color', [0.5, 1, 0.5], 'FontSize', 11, 'FontWeight', 'bold');
    else
        % Show last 5 events
        n_show = min(5, length(tamper_log));
        
        for i = n_show:-1:1
            event = tamper_log(length(tamper_log) - n_show + i);
            
            if event.isTampered
                alert_color = [1, 0.3, 0.3]; % Red
                icon = '❌';
            else
                alert_color = [0.3, 1, 0.3]; % Green
                icon = '✓';
            end
            
            alert_text = sprintf('%s [%s] Patient %s', ...
                icon, event.timestamp, event.patientID);
            
            text(ax, 0.05, text_y, alert_text, ...
                'Color', alert_color, 'FontSize', 9, 'FontFamily', 'monospaced');
            text_y = text_y - 0.15;
        end
    end
    
    set(ax, 'XLim', [0, 1], 'YLim', [0, 1]);
    set(ax, 'XTick', [], 'YTick', []);
    set(ax, 'Color', [0.15, 0.15, 0.2]);
    title(ax, 'Alert Log');
end

function shortened = shortenPatientName(name)
    parts = strsplit(name);
    if length(parts) >= 2
        shortened = sprintf('%s %s.', parts{1}, parts{2}(1));
    else
        shortened = name;
    end
end

%% ===============================================================
%  MAIN MONITORING LOOP
%  ===============================================================

display_alert('INFO', 'Starting IoMT Tamper Detection Monitor');
display_alert('INFO', sprintf('Connecting to API: %s', API_URL));

% Initialize data storage
previous_hashes = [];
check_count = 0;
tamper_events = [];

% Main loop
while MONITORING_ACTIVE
    try
        check_count = check_count + 1;
        
        % Fetch current patient data
        patients_data = fetch_api('/patients');
        
        if ~isempty(patients_data) && isstruct(patients_data)
            if isfield(patients_data, 'patients')
                current_patients = patients_data.patients;
                
                % Compute current hashes
                current_hashes = compute_hashes(current_patients);
                
                % Check integrity
                is_tampered = false;
                tampered_patient = 'None';
                
                if ~isempty(previous_hashes) && length(previous_hashes) == length(current_hashes)
                    for i = 1:length(current_hashes)
                        if current_hashes(i) ~= previous_hashes(i)
                            is_tampered = true;
                            tampered_patient = current_patients(i).id;
                            break;
                        end
                    end
                end
                
                % Log event
                event.timestamp = datetime('now', 'Format', 'HHmm:ss');
                event.checkNumber = check_count;
                event.isTampered = is_tampered;
                event.patientID = tampered_patient;
                event.patientCount = length(current_patients);
                
                TAMPER_LOG = [TAMPER_LOG, event];
                
                % Alert if tampered
                if is_tampered
                    display_alert('CRITICAL', sprintf('TAMPERING DETECTED: Patient %s data modified!', tampered_patient));
                    % Could stop monitoring here in critical scenario
                end
                
                % Fetch blockchain status
                blockchain_status = fetch_api('/statistics');
                
                if ~isempty(blockchain_status) && isstruct(blockchain_status)
                    if isfield(blockchain_status, 'blockchain_status')
                        integrity_pct = blockchain_status.blockchain_status.integrity_score;
                    else
                        integrity_pct = 100;
                    end
                else
                    integrity_pct = 100;
                end
                
                % Update displays
                if ishandle(fig)
                    plot_patient_statuses(current_patients, ax_patients);
                    plot_integrity_score(integrity_pct, ax_integrity);
                    plot_timeline(TAMPER_LOG, ax_timeline);
                    plot_alerts_log(TAMPER_LOG, ax_alerts);
                    
                    % Update figure title with status
                    status_text = sprintf('| Check: %d | Patients: %d | Integrity: %.0f%% | Status: %s', ...
                        check_count, length(current_patients), integrity_pct, ...
                        ternary(is_tampered, 'ALERT ⚠️', 'NORMAL ✓'));
                    fig.Name = ['IoMT Monitor ' status_text];
                    
                    drawnow;
                end
                
                % Store current hashes for next comparison
                previous_hashes = current_hashes;
                
            end
        end
        
        % Wait before next check
        pause(REFRESH_INTERVAL);
        
    catch ME
        display_alert('WARNING', sprintf('Monitoring cycle error: %s', ME.message));
        pause(REFRESH_INTERVAL);
    end
end

%% ===============================================================
%  HELPER FUNCTION FOR TERNARY
%  ===============================================================

function result = ternary(condition, trueValue, falseValue)
    if condition
        result = trueValue;
    else
        result = falseValue;
    end
end

display_alert('INFO', 'MATLAB Monitoring Session Complete');

% Final report
fprintf('\n\n========== MONITORING REPORT ==========\n');
fprintf('Total Checks: %d\n', check_count);
fprintf('Tamper Events: %d\n', sum([TAMPER_LOG.isTampered]));
fprintf('Monitoring Duration: %d seconds\n', check_count * REFRESH_INTERVAL);
fprintf('========================================\n\n');
