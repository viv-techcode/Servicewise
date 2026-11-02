/* TearCalendar
 * Tweak here: HOLD_SECONDS, CORNER_SECONDS, BASE_TEAR_SECONDS, SPEED_UP_FACTOR,
 * WHIP_PAN_SECONDS, and COLORS. The component intentionally animates only
 * transform, opacity, and filter for a stable mobile frame rate.
 */
(function () {
    'use strict';

    const HOLD_SECONDS = 3;
    const CORNER_SECONDS = 0.3;
    const BASE_TEAR_SECONDS = 1;
    const WHIP_PAN_SECONDS = 2;
    const DEFAULT_SPEED_UP_FACTOR = 0.8;
    const COLORS = {
        background: '#5CC8FA',
        body: '#26485A',
        front: '#FFF5E0',
        back: '#E2DACB',
        orange: '#F59A0E',
        hook: '#A67C2E',
        outline: '#2B2B2B'
    };

    const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

    class TearCalendar {
        constructor(root, options = {}) {
            this.root = root;
            this.options = {
                startDate: new Date(),
                daysToTear: 8,
                trigger: 'scroll',
                loop: false,
                speedUpFactor: DEFAULT_SPEED_UP_FACTOR,
                whipPanAtEnd: false,
                initialValue: 1,
                maxValue: 30,
                onChange: () => {},
                ...options
            };
            this.value = this.options.initialValue;
            this.running = false;
            this.transitioning = false;
            this.wheelDelta = 0;
            this.touchStartY = null;
            this.master = null;
            this.idle = null;
            this.scrollTrigger = null;
            this.reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            this.sheet = root.querySelector('#paperSheet');
            this.display = root.querySelector('#vehicleAgeDisplay');
            this.label = root.querySelector('.calendar-label');
            this.status = root.parentElement.querySelector('#vehicleAgeStatus');
            this.input = root.parentElement.querySelector('#vehicle_age');
            this.previous = root.parentElement.querySelector('#vehicleAgePrev');
            this.next = root.parentElement.querySelector('#vehicleAgeNext');
            this.bind();
            this.render();
        }

        bind() {
            this.root.addEventListener('wheel', (event) => {
                event.preventDefault();
                this.wheelDelta += event.deltaY;
                if (Math.abs(this.wheelDelta) < 28) return;
                const direction = this.wheelDelta > 0 ? 1 : -1;
                this.wheelDelta = 0;
                this.step(direction);
            }, { passive: false });
            this.root.addEventListener('touchstart', (event) => {
                this.touchStartY = event.touches[0].clientY;
            }, { passive: true });
            this.root.addEventListener('touchend', (event) => {
                if (this.touchStartY === null) return;
                const delta = this.touchStartY - event.changedTouches[0].clientY;
                this.touchStartY = null;
                if (Math.abs(delta) > 28) this.step(delta > 0 ? 1 : -1);
            }, { passive: true });
            this.previous?.addEventListener('click', () => this.step(-1));
            this.next?.addEventListener('click', () => this.step(1));
            if (this.options.trigger === 'click') this.root.addEventListener('click', () => this.play());
            if (this.options.trigger === 'load') this.play();
            if (this.options.trigger === 'scroll' && window.gsap && window.ScrollTrigger) {
                gsap.registerPlugin(ScrollTrigger);
                this.scrollTrigger = ScrollTrigger.create({
                    trigger: this.root,
                    start: 'top 80%',
                    once: true,
                    onEnter: () => this.play()
                });
            }
        }

        render() {
            const progress = (this.value - 1) / (this.options.maxValue - 1);
            this.display.textContent = String(this.value);
            if (this.label) this.label.textContent = this.options.startDate.toLocaleString('en-US', { month: 'long' }).toUpperCase();
            this.status.textContent = `${String(this.value).padStart(2, '0')} / ${this.options.maxValue}`;
            this.input.value = String(this.value);
            this.previous.disabled = this.transitioning || this.value <= 1;
            this.next.disabled = this.transitioning || this.value >= this.options.maxValue;
            this.root.style.setProperty('--age-ratio', progress.toFixed(3));
            this.root.style.setProperty('--paper-color', `rgb(${this.colorAt(progress).join(', ')})`);
            this.root.style.setProperty('--paper-ink', progress > 0.52 ? '#fff1c7' : '#2B2B2B');
            this.options.onChange(this.value);
        }

        colorAt(progress) {
            const stops = [[255, 255, 255], [255, 244, 190], [255, 211, 52], [194, 116, 37], [91, 48, 29], [30, 22, 24]];
            const scaled = progress * (stops.length - 1);
            const index = Math.min(stops.length - 2, Math.floor(scaled));
            const ratio = scaled - index;
            return stops[index].map((channel, i) => Math.round(channel + (stops[index + 1][i] - channel) * ratio));
        }

        duration() {
            return Math.max(0.2, BASE_TEAR_SECONDS * Math.pow(this.options.speedUpFactor, Math.max(0, this.value - 2)));
        }

        step(direction) {
            if (this.transitioning) return;
            const nextValue = clamp(this.value + direction, 1, this.options.maxValue);
            if (nextValue === this.value) return;
            if (this.reducedMotion) {
                gsap.to(this.sheet, { duration: 0.18, opacity: 0, onComplete: () => {
                    this.value = nextValue;
                    this.render();
                    gsap.to(this.sheet, { duration: 0.18, opacity: 1 });
                }});
                return;
            }
            this.transitioning = true;
            this.render();
            const outgoing = this.createFlight(direction);
            const duration = this.duration();
            gsap.timeline({
                onComplete: () => {
                    outgoing.remove();
                    this.value = nextValue;
                    this.render();
                    this.transitioning = false;
                    this.render();
                }
            })
                .to(this.sheet, { duration: CORNER_SECONDS, x: direction > 0 ? 10 : -10, y: -25, rotate: direction * -4, skewX: -4, ease: 'power1.out' })
                .to(outgoing, { duration: duration, x: direction > 0 ? 520 : -520, y: direction > 0 ? -180 : 120, rotate: direction > 0 ? 18 : -18, rotateX: -150, skewX: direction > 0 ? -8 : 8, opacity: 0.05, ease: 'power2.in' }, '<')
                .set(outgoing.querySelector('.paper-front'), { opacity: 0 }, `>-=${duration * 0.5}`)
                .set(outgoing.querySelector('.paper-back'), { opacity: 1 }, '<')
                .to(this.sheet, { duration: duration * 0.5, x: 0, y: 0, rotate: 0, skewX: 0, ease: 'back.out(1.7)' }, `>-=${duration * 0.45}`);
        }

        createFlight(direction) {
            const flight = this.sheet.cloneNode(true);
            flight.classList.add('calendar-flight');
            flight.classList.remove('paper-sheet');
            flight.style.zIndex = '5';
            flight.style.transformOrigin = direction > 0 ? '100% 0%' : '0% 0%';
            flight.querySelector('.paper-year').textContent = this.value;
            this.sheet.parentElement.appendChild(flight);
            return flight;
        }

        play() {
            if (this.running || !window.gsap) return;
            this.running = true;
            this.idle = gsap.to(this.root.querySelector('.paper-stack'), { duration: HOLD_SECONDS, rotate: 1, yoyo: true, repeat: -1, ease: 'sine.inOut' });
            this.runSequence(0);
        }

        runSequence(completed) {
            if (!this.running) return;
            if (completed >= this.options.daysToTear || this.value >= this.options.maxValue) {
                if (this.options.whipPanAtEnd) this.whipPan();
                if (this.options.loop) {
                    this.reset();
                    this.play();
                } else {
                    this.pause();
                }
                return;
            }
            const delay = completed === 0 ? HOLD_SECONDS * 1000 : Math.max(120, this.duration() * 1000 * 0.45);
            this.autoplayTimer = window.setTimeout(() => {
                if (!this.running) return;
                if (this.transitioning) {
                    this.runSequence(completed);
                    return;
                }
                this.step(1);
                this.runSequence(completed + 1);
            }, delay);
        }

        whipPan() {
            const pages = this.root.querySelectorAll('.calendar-flight');
            gsap.to(this.root.querySelector('.paper-stack'), { duration: WHIP_PAN_SECONDS, xPercent: -120, ease: 'power3.in' });
            gsap.to(pages, { duration: WHIP_PAN_SECONDS, x: 440, rotation: 18, skewX: 9, stagger: 0.08, filter: 'blur(2px)', ease: 'power3.in' });
        }

        pause() {
            this.running = false;
            window.clearTimeout(this.autoplayTimer);
            this.master?.pause();
            this.idle?.pause();
        }

        reset() {
            this.pause();
            if (this.master) this.master.kill();
            if (this.idle) this.idle.kill();
            this.value = this.options.initialValue;
            gsap.set(this.sheet, { clearProps: 'all' });
            this.root.querySelectorAll('.calendar-flight').forEach(page => page.remove());
            this.render();
        }

        destroy() {
            this.pause();
            this.scrollTrigger?.kill();
            this.master?.kill();
            this.idle?.kill();
            this.root.querySelectorAll('.calendar-flight').forEach(page => page.remove());
        }
    }

    window.TearCalendar = TearCalendar;
})();
