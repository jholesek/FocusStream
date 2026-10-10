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

    const timerDisplay = document.getElementById('timer-display');
    const startPauseBtn = document.getElementById('start-pause-btn');
    const resetBtn = document.getElementById('reset-btn');
    const progressBar = document.getElementById('timer-progress');
    const modeButtons = document.querySelectorAll('[data-timer-mode]');

    function playChime() {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
            osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.3); // A5
            gain.gain.setValueAtTime(0.3, ctx.currentTime);
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
        const progress = ((total - timeLeft) / total) * 100;
        if (progressBar) progressBar.style.width = `${progress}%`;
    }

    function switchMode(newMode) {
        mode = newMode;
        pauseTimer();
        timeLeft = durations[mode];
        modeButtons.forEach(btn => {
            const active = btn.dataset.timerMode === newMode;
            btn.className = active 
                ? 'px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 transition-all'
                : 'px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-all';
        });
        updateDisplay();
    }

    function startTimer() {
        if (isRunning) return;
        isRunning = true;
        if (startPauseBtn) {
            startPauseBtn.textContent = 'Pause';
            startPauseBtn.classList.remove('bg-indigo-600', 'hover:bg-indigo-500');
            startPauseBtn.classList.add('bg-amber-600', 'hover:bg-amber-500');
        }

        timerInterval = setInterval(() => {
            if (timeLeft > 0) {
                timeLeft--;
                updateDisplay();
            } else {
                pauseTimer();
                playChime();
                if (Notification.permission === 'granted') {
                    new Notification("Focus Stream", { body: `${mode === 'focus' ? 'Focus block' : 'Break'} complete! Take a moment.` });
                }
            }
        }, 1000);
    }

    function pauseTimer() {
        isRunning = false;
        clearInterval(timerInterval);
        timerInterval = null;
        if (startPauseBtn) {
            startPauseBtn.textContent = 'Start';
            startPauseBtn.classList.remove('bg-amber-600', 'hover:bg-amber-500');
            startPauseBtn.classList.add('bg-indigo-600', 'hover:bg-indigo-500');
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

    modeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            switchMode(btn.dataset.timerMode);
        });
    });

    // Init
    updateDisplay();
})();
