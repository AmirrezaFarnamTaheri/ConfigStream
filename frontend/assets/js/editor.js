/**
 * Monaco Editor Integration for ConfigStream Lab
 */
import * as monaco from 'monaco-editor';

let editorInstance = null;

function initEditor(containerId, initialValue = '', language = 'json') {
    const container = document.getElementById(containerId);
    if (!container) return null;

    // Clean up previous instance
    if (editorInstance) {
        editorInstance.dispose();
    }

    editorInstance = monaco.editor.create(container, {
        value: initialValue,
        language: language,
        theme: 'vs-dark',
        minimap: { enabled: false },
        automaticLayout: true,
        scrollBeyondLastLine: false,
        fontSize: 14,
        fontFamily: "'Fira Code', 'Consolas', monospace",
        padding: { top: 10, bottom: 10 }
    });

    return editorInstance;
}

function getEditorValue() {
    return editorInstance ? editorInstance.getValue() : '';
}

function setEditorValue(value) {
    if (editorInstance) {
        editorInstance.setValue(value);
    }
}

// Expose globally for legacy script integration
window.LabEditor = {
    init: initEditor,
    getValue: getEditorValue,
    setValue: setEditorValue,
    instance: () => editorInstance
};
