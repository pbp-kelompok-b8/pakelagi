(() => {
    const intro = document.getElementById('site-intro');
    if (!intro) return;
    try {
        if (sessionStorage.getItem('pakelagi_intro')) return;
        sessionStorage.setItem('pakelagi_intro', '1');
    } catch {
        return;
    }
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (motion.matches) return;

    const frames = [...intro.querySelectorAll('.intro__frame')];
    const button = intro.querySelector('button');
    const previousFocus = document.activeElement;
    const events = new AbortController();
    let finished = false;
    let timer;
    const finish = () => {
        if (finished) return;
        finished = true;
        clearTimeout(timer);
        events.abort();
        intro.hidden = true;
        if (intro.contains(document.activeElement)) {
            const target = previousFocus === document.body
                ? document.querySelector('main') : previousFocus;
            if (target) {
                if (!target.hasAttribute('tabindex')) {
                    target.setAttribute('tabindex', '-1');
                    target.addEventListener('blur', () => target.removeAttribute('tabindex'), { once: true });
                }
                target.focus({ preventScroll: true });
            }
        }
    };
    intro.addEventListener('focusout', event => {
        if (!intro.contains(event.relatedTarget)) finish();
    }, { signal: events.signal });
    intro.addEventListener('click', finish, { signal: events.signal });
    for (const name of ['wheel', 'touchmove']) {
        window.addEventListener(name, finish, { passive: true, signal: events.signal });
    }
    window.addEventListener('keydown', event => {
        if (['Escape', 'PageDown', 'PageUp', 'ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) finish();
    }, { signal: events.signal });
    motion.addEventListener('change', event => {
        if (event.matches) finish();
    }, { signal: events.signal });
    // A stalled connection must not leave the page behind a loading overlay.
    timer = setTimeout(finish, 5000);
    const showFrame = index => {
        if (finished) return;
        if (index === frames.length) {
            intro.querySelector('.intro__photos').hidden = true;
            intro.querySelector('.intro__end').hidden = false;
            timer = setTimeout(() => {
                intro.classList.add('intro--leaving');
                timer = setTimeout(finish, 600);
            }, 600);
            return;
        }
        frames.forEach((frame, i) => { frame.hidden = i !== index; });
        const progress = frames[index].dataset.progress;
        intro.querySelector('[role="progressbar"]').setAttribute('aria-valuenow', progress);
        intro.querySelector('.intro__counter').textContent = `[ ${progress.padStart(2, '0')} ]`;
        intro.querySelector('.intro__bar').style.width = `${progress}%`;
        timer = setTimeout(() => showFrame(index + 1), 180);
    };
    Promise.all([...intro.querySelectorAll('img')].map(image => image.decode()))
        .then(() => {
            clearTimeout(timer);
            if (!finished) {
                intro.hidden = false;
                button.focus({ preventScroll: true });
                showFrame(0);
            }
        })
        .catch(finish);
})();
