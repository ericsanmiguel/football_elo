/**
 * DOM helpers and formatting utilities.
 */

export function $(selector, parent = document) {
    return parent.querySelector(selector);
}

export function $$(selector, parent = document) {
    return [...parent.querySelectorAll(selector)];
}

export function el(tag, attrs = {}, children = []) {
    const elem = document.createElement(tag);
    for (const [key, val] of Object.entries(attrs)) {
        if (key === 'class') elem.className = val;
        else if (key === 'html') elem.innerHTML = val;
        else if (key === 'text') elem.textContent = val;
        else if (key.startsWith('on')) elem.addEventListener(key.slice(2), val);
        else elem.setAttribute(key, val);
    }
    for (const child of children) {
        if (typeof child === 'string') elem.appendChild(document.createTextNode(child));
        else if (child) elem.appendChild(child);
    }
    return elem;
}

export function flagImg(code, alt, size = 'sm') {
    if (!code) return null;
    const w = size === 'lg' ? 160 : 40;
    const img = document.createElement('img');
    img.src = `https://flagcdn.com/w${w}/${code}.png`;
    img.alt = alt;
    img.className = `flag-${size}`;
    img.loading = 'lazy';
    return img;
}

export function formatRating(r) {
    return Math.round(r).toString();
}

export function formatChange(change) {
    if (change > 0) return `+${change.toFixed(1)}`;
    if (change < 0) return change.toFixed(1);
    return '0.0';
}

export function changeClass(change) {
    if (change > 0.05) return 'change-positive';
    if (change < -0.05) return 'change-negative';
    return 'change-neutral';
}
