// Focus Stream Pomodoro Timer
(() => {
    let mode = 'focus'; // focus, shortBreak, longBreak
    const durations = {
        focus: 25 * 60,
        shortBreak: 5 * 60,
        longBreak: 15 * 60
    };
    let timeLeft = durations.focus;
    let timerInterval = null;
    let isRunning = false;

    const CIRCLE_RADIUS = 100;
    const CIRCUMFERENCE = 2 * Math.PI * CIRCLE_RADIUS; // ~628.318

    // DOM Elements
    const timerDisplay = document.getElementById('timer-display');
    const startPauseBtn = document.getElementById('start-pause-btn');
    const resetBtn = document.getElementById('reset-btn');
    const addTimeBtn = document.getElementById('add-time-btn');
    const testToastBtn = document.getElementById('test-toast-btn');
    const progressBar = document.getElementById('timer-progress');
    const circleProgress = document.getElementById('timer-circle-progress');
    const timerGlow = document.getElementById('timer-glow');
    const modeBadge = document.getElementById('timer-mode-badge');
    const taskInput = document.getElementById('timer-task-input');
    const targetLabel = document.getElementById('timer-target-label');
    const modeButtons = document.querySelectorAll('[data-timer-mode]');

    function playChime() {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
            osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.3); // A5
            gain.gain.setValueAtTime(0.35, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 1.2);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + 1.2);
        } catch (e) {
            console.log("Audio notification skipped");
        }
    }

    function formatTime(seconds) {
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }

    function updateDisplay() {
        const formatted = formatTime(timeLeft);
        if (timerDisplay) timerDisplay.textContent = formatted;
        document.title = isRunning ? `(${formatted}) Focus Stream` : 'Focus Stream — Flow State Task & Timer';

        const total = durations[mode];
        const progress = total > 0 ? ((total - timeLeft) / total) : 0; // 0 to 1

        // Linear progress fallback
        if (progressBar) progressBar.style.width = `${progress * 100}%`;

        // Circular progress ring
        if (circleProgress) {
            circleProgress.style.strokeDasharray = `${CIRCUMFERENCE}`;
            // Fills smoothly clockwise from 12 o'clock as time progresses
            const offset = CIRCUMFERENCE * (1 - progress);
            circleProgress.style.strokeDashoffset = `${offset}`;
        }

        // Mode badge update
        if (modeBadge) {
            if (mode === 'focus') {
                modeBadge.textContent = '⚡ Focus Mode';
                modeBadge.className = 'px-3 py-1 rounded-full text-[11px] font-bold tracking-wider uppercase bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 shadow-sm shadow-indigo-500/10';
            } else if (mode === 'shortBreak') {
                modeBadge.textContent = '☕ Short Break';
                modeBadge.className = 'px-3 py-1 rounded-full text-[11px] font-bold tracking-wider uppercase bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 shadow-sm shadow-emerald-500/10';
            } else {
                modeBadge.textContent = '🌴 Long Break';
                modeBadge.className = 'px-3 py-1 rounded-full text-[11px] font-bold tracking-wider uppercase bg-cyan-500/15 border border-cyan-500/30 text-cyan-300 shadow-sm shadow-cyan-500/10';
            }
        }

        // Ambient glow container pulse
        if (timerGlow) {
            if (isRunning) {
                timerGlow.classList.remove('opacity-30', 'scale-95');
                timerGlow.classList.add('opacity-80', 'scale-105');
            } else {
                timerGlow.classList.remove('opacity-80', 'scale-105');
                timerGlow.classList.add('opacity-30', 'scale-95');
            }
        }

        // Target label update
        if (targetLabel && taskInput) {
            targetLabel.textContent = taskInput.value.trim() || 'Focus Session';
        }
    }

    function switchMode(newMode) {
        mode = newMode;
        pauseTimer();
        timeLeft = durations[mode];
        modeButtons.forEach(btn => {
            const active = btn.dataset.timerMode === newMode;
            btn.className = active 
                ? 'px-3 py-1.5 rounded-xl text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 shadow-sm shadow-indigo-500/20 transition-all'
                : 'px-3 py-1.5 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800/80 transition-all';
        });
        updateDisplay();
    }

    function showToast(options = {}) {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const currentTask = (taskInput && taskInput.value.trim()) || options.taskName || 'Deep Work Session';
        const durationMinutes = Math.round(durations[mode] / 60);
        const isFocus = mode === 'focus';
        const title = options.title || (isFocus ? 'Focus Session Complete! ⚡' : 'Break Finished! 🔔');
        const message = options.message || (isFocus
            ? `Great focus momentum on "${currentTask}"! Time to rest or log your session.`
            : 'Break is up. Ready to lock into your next focus stream?');

        const toastId = 'toast-' + Date.now();
        const toast = document.createElement('div');
        toast.id = toastId;
        toast.className = 'group relative overflow-hidden bg-slate-900/95 border border-indigo-500/40 text-slate-100 p-4 rounded-2xl shadow-2xl shadow-black/80 backdrop-blur-xl pointer-events-auto transform translate-y-3 opacity-0 transition-all duration-300 ease-out border-l-4 border-l-indigo-500';

        const safeTaskName = currentTask.replace(/"/g, '&quot;');

        toast.innerHTML = `
            <div class="flex items-start space-x-3.5">
                <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-500 to-cyan-400 flex items-center justify-center text-white flex-shrink-0 shadow-md shadow-indigo-500/30">
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                </div>
                <div class="flex-1 min-w-0 pr-6">
                    <h4 class="text-sm font-bold text-white tracking-tight">${title}</h4>
                    <p class="text-xs text-slate-300 mt-1 leading-relaxed">${message}</p>
                    
                    ${isFocus ? `
                    <form hx-post="/sessions" hx-target="#sessions-list" hx-swap="outerHTML" class="mt-3">
                        <input type="hidden" name="task_name" value="${safeTaskName}">
                        <input type="hidden" name="duration_minutes" value="${durationMinutes}">
                        <input type="hidden" name="energy_rating" value="4">
                        <button type="submit" onclick="dismissToast('${toastId}')" class="w-full py-2 px-3 rounded-xl bg-gradient-to-r from-indigo-600 via-indigo-500 to-cyan-500 hover:from-indigo-500 hover:to-cyan-400 text-white font-semibold text-xs transition-all shadow-md shadow-indigo-600/30 flex items-center justify-center space-x-1.5 active:scale-95">
                            <svg class="w-3.5 h-3.5 stroke-[2.5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
                            </svg>
                            <span>Record to Today's Log</span>
                        </button>
                    </form>
                    ` : ''}
                </div>
                <button type="button" onclick="dismissToast('${toastId}')" class="absolute top-3 right-3 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors" title="Dismiss notification">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>
            <div class="w-full bg-slate-800/80 h-1 rounded-full mt-3 overflow-hidden">
                <div id="${toastId}-progress" class="bg-gradient-to-r from-indigo-500 to-cyan-400 h-1 rounded-full transition-all duration-[6000ms] ease-linear" style="width: 100%"></div>
            </div>
        `;

        container.appendChild(toast);
        if (window.htmx) {
            window.htmx.process(toast);
        }

        // Entrance animation
        requestAnimationFrame(() => {
            toast.classList.remove('translate-y-3', 'opacity-0');
            toast.classList.add('translate-y-0', 'opacity-100');
            const p = document.getElementById(`${toastId}-progress`);
            if (p) {
                requestAnimationFrame(() => {
                    p.style.width = '0%';
                });
            }
        });

        // Auto-dismiss after 6.5 seconds
        const dismissTimer = setTimeout(() => {
            dismissToast(toastId);
        }, 6500);
        toast.dataset.dismissTimer = dismissTimer;
    }

    window.dismissToast = function(id) {
        const el = document.getElementById(id);
        if (!el) return;
        if (el.dataset.dismissTimer) clearTimeout(el.dataset.dismissTimer);
        el.classList.remove('translate-y-0', 'opacity-100');
        el.classList.add('translate-y-2', 'opacity-0');
        setTimeout(() => {
            if (el.parentNode) el.parentNode.removeChild(el);
        }, 300);
    };

    window.triggerFocusToast = function(customTitle, customMessage) {
        showToast({ title: customTitle, message: customMessage });
    };

    function startTimer() {
        if (isRunning) return;
        isRunning = true;
        if (startPauseBtn) {
            startPauseBtn.innerHTML = `
                <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
                <span>Pause</span>
            `;
            startPauseBtn.classList.remove('from-indigo-600', 'to-indigo-500', 'hover:from-indigo-500', 'hover:to-indigo-400', 'shadow-indigo-600/30');
            startPauseBtn.classList.add('from-amber-600', 'to-amber-500', 'hover:from-amber-500', 'hover:to-amber-400', 'shadow-amber-600/30');
        }

        updateDisplay();

        timerInterval = setInterval(() => {
            if (timeLeft > 0) {
                timeLeft--;
                updateDisplay();
            } else {
                pauseTimer();
                playChime();
                showToast();
                if (Notification && Notification.permission === 'granted') {
                    new Notification("Focus Stream", { 
                        body: `${mode === 'focus' ? 'Focus block' : 'Break'} complete! Take a moment.` 
                    });
                }
            }
        }, 1000);
    }

    function pauseTimer() {
        isRunning = false;
        clearInterval(timerInterval);
        timerInterval = null;
        if (startPauseBtn) {
            startPauseBtn.innerHTML = `
                <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                <span>Start Session</span>
            `;
            startPauseBtn.classList.remove('from-amber-600', 'to-amber-500', 'hover:from-amber-500', 'hover:to-amber-400', 'shadow-amber-600/30');
            startPauseBtn.classList.add('from-indigo-600', 'to-indigo-500', 'hover:from-indigo-500', 'hover:to-indigo-400', 'shadow-indigo-600/30');
        }
        updateDisplay();
    }

    function resetTimer() {
        pauseTimer();
        timeLeft = durations[mode];
        updateDisplay();
    }

    // Attach listeners
    if (startPauseBtn) {
        startPauseBtn.addEventListener('click', () => {
            if (isRunning) {
                pauseTimer();
            } else {
                if (Notification && Notification.permission === 'default') {
                    Notification.requestPermission();
                }
                startTimer();
            }
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener('click', resetTimer);
    }

    if (addTimeBtn) {
        addTimeBtn.addEventListener('click', () => {
            timeLeft += 5 * 60;
            durations[mode] += 5 * 60;
            updateDisplay();
        });
    }

    if (testToastBtn) {
        testToastBtn.addEventListener('click', () => {
            showToast({
                title: 'Toast Notification Preview 🚀',
                message: 'This is a live preview of the completion toast that pops up when your countdown finishes!'
            });
        });
    }

    if (taskInput) {
        taskInput.addEventListener('input', () => {
            if (targetLabel) {
                targetLabel.textContent = taskInput.value.trim() || 'Focus Session';
            }
        });
    }

    modeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            switchMode(btn.dataset.timerMode);
        });
    });

    // Init
    updateDisplay();
})();
