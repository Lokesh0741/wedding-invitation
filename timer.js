(function(){
    const el = document.getElementById('timer');
    if (!el) return;
    
    // Get date from HTML data attribute
    const dateStr = el.dataset.date;
    if (!dateStr) return;
    
    // Replace 'T' with space if needed, but new Date handles ISO strings well
    const target = new Date(dateStr).getTime();
    if (isNaN(target)) return;

    function tick(){
        let diff = target - Date.now();
        if (diff < 0) diff = 0;
        
        const d = Math.floor(diff / 86400000);
        const h = Math.floor((diff % 86400000) / 3600000);
        const m = Math.floor((diff % 3600000) / 60000);
        const s = Math.floor((diff % 60000) / 1000);
        
        const daysEl = document.getElementById('days');
        const hoursEl = document.getElementById('hours');
        const minutesEl = document.getElementById('minutes');
        const secondsEl = document.getElementById('seconds');
        
        if(daysEl) daysEl.textContent = d;
        if(hoursEl) hoursEl.textContent = h;
        if(minutesEl) minutesEl.textContent = m;
        if(secondsEl) secondsEl.textContent = s;
    }
    
    tick(); 
    setInterval(tick, 1000);
})();