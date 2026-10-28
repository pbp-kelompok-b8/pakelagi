// Run with: node --test moderations/test_publish_modal.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const template = fs.readFileSync(
    path.join(__dirname, '../templates/moderations/components/publish_modal.html'),
    'utf8',
);
const script = template.match(/<script>([\s\S]*?)<\/script>/)[1];

test('publish modal can reopen and close after each successful HTMX request', () => {
    let elements;
    const context = vm.createContext({
        document: { getElementById: id => elements[id] },
        setTimeout: callback => callback(),
    });

    for (let opening = 0; opening < 3; opening++) {
        const listeners = [];
        elements = {
            'publish-form': {
                addEventListener(event, listener) {
                    assert.equal(event, 'htmx:afterRequest');
                    listeners.push(listener);
                },
            },
            'publish-modal-overlay': { style: { opacity: '1' } },
            'modal-container': { innerHTML: 'open' },
        };

        // Classic scripts injected by HTMX share the same global scope.
        vm.runInContext(script, context);
        assert.equal(listeners.length, 1);
        listeners[0]({ detail: { successful: false } });
        assert.equal(elements['modal-container'].innerHTML, 'open');
        listeners[0]({ detail: { successful: true } });
        assert.equal(elements['publish-modal-overlay'].style.opacity, '0');
        assert.equal(elements['modal-container'].innerHTML, '');
    }
});
