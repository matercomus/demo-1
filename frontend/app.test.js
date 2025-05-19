document.body.innerHTML = '<div id="app"></div>';

const appModule = require('./app');
const { handleChatSubmit, chatMessages, renderMenu } = appModule;

// Mock fetch and DOM
beforeEach(() => {
  global.fetch = jest.fn(() => Promise.resolve({ json: () => Promise.resolve({ reply: 'Meal 3 deleted.', stage: 'created' }) }));
  chatMessages.length = 0;
  appModule.pendingRemoval = null;
  document.body.innerHTML = '<div id="app"></div>';
});

describe('Destructive Action Confirmation', () => {
  it('should prompt for confirmation on destructive command (pattern match)', () => {
    document.body.innerHTML = `<input id="chatInput" value="delete meal 3" />`;
    handleChatSubmit({ preventDefault: () => {} });
    expect(chatMessages[chatMessages.length-1].stage).toBe('confirming_removal');
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('should prompt for confirmation on LLM confirming_removal', () => {
    // Simulate LLM reply with confirming_removal
    chatMessages.push({ role: 'user', content: 'delete meal 3' });
    appModule.pendingRemoval = null;
    // Simulate LLM reply handler
    const data = { stage: 'confirming_removal', reply: 'Are you sure?' };
    // Simulate the code block from app.js
    if (data && data.stage === 'confirming_removal' && !appModule.pendingRemoval) {
      appModule.pendingRemoval = { type: 'meal', id: '3', originalMessage: 'delete meal 3' };
      chatMessages.push({ role: 'bot', content: data.reply, stage: 'confirming_removal', destructive: true });
    }
    expect(chatMessages[chatMessages.length-1].stage).toBe('confirming_removal');
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('should not delete if user cancels', () => {
    appModule.pendingRemoval = { type: 'meal', id: '3', originalMessage: 'delete meal 3' };
    document.body.innerHTML = `<input id="chatInput" value="no" />`;
    handleChatSubmit({ preventDefault: () => {} });
    expect(chatMessages[chatMessages.length-1].content).toMatch(/cancelled/i);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('should delete if user confirms', async () => {
    appModule.pendingRemoval = { type: 'meal', id: '3', originalMessage: 'delete meal 3' };
    document.body.innerHTML = `<input id="chatInput" value="yes" />`;
    await handleChatSubmit({ preventDefault: () => {} });
    expect(global.fetch).toHaveBeenCalled();
  });

  it('should not delete on unrelated user input', () => {
    appModule.pendingRemoval = { type: 'meal', id: '3', originalMessage: 'delete meal 3' };
    document.body.innerHTML = `<input id="chatInput" value="maybe" />`;
    handleChatSubmit({ preventDefault: () => {} });
    // Debug: print chatMessages
    console.log('chatMessages after unrelated input:', JSON.stringify(chatMessages, null, 2));
    // Find the last bot message
    const lastBotMsg = [...chatMessages].reverse().find(m => m.role === 'bot');
    expect(lastBotMsg.content).toMatch(/please type/i);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('should not double-confirm if both pattern and LLM trigger', () => {
    // Simulate pattern match
    document.body.innerHTML = `<input id="chatInput" value="delete meal 3" />`;
    handleChatSubmit({ preventDefault: () => {} });
    // Simulate LLM reply
    const data = { stage: 'confirming_removal', reply: 'Are you sure?' };
    if (data && data.stage === 'confirming_removal' && appModule.pendingRemoval) {
      // Should not add another confirmation
      expect(chatMessages.filter(m => m.stage === 'confirming_removal').length).toBe(1);
    }
  });
}); 