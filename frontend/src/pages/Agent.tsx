import React, { useState, useRef, useEffect } from 'react';
import { api } from '../api';
import { Bot, Send, Terminal, Wrench } from 'lucide-react';

interface ChatMessage {
  id: string;
  role: 'user' | 'agent';
  content: string;
  tools?: string[];
  isThinking?: boolean;
}

export const Agent: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      role: 'agent',
      content: 'Hello. I am the Strands AI Orchestration Agent.\nI have access to live inventory risk, transfer operations, and historical OpenSearch intelligence.\n\nHow can I assist your recovery operations today?'
    }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim()
    };
    
    const typingMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      role: 'agent',
      content: '',
      isThinking: true
    };

    setMessages(prev => [...prev, userMessage, typingMessage]);
    setInput('');
    setIsTyping(true);

    try {
      const response = await api.askAgent(userMessage.content);
      
      setMessages(prev => prev.map(msg => 
        msg.id === typingMessage.id 
          ? { ...msg, content: response.answer, isThinking: false, tools: response.tools_used } 
          : msg
      ));
    } catch (error) {
      setMessages(prev => prev.map(msg => 
        msg.id === typingMessage.id 
          ? { ...msg, content: "ERROR: Connection to Strands Agent failed. Please check network telemetry.", isThinking: false } 
          : msg
      ));
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="h-[calc(100vh-80px)] flex flex-col space-y-6">
      
      {/* Header */}
      <div className="flex justify-between items-end shrink-0">
        <div>
          <h1 className="text-xl font-bold text-text-primary tracking-tight flex items-center space-x-2">
            <Terminal className="h-5 w-5 text-semantic-blue" />
            <span>Strands Agent Terminal</span>
          </h1>
          <p className="text-text-secondary mt-1 text-sm font-mono uppercase tracking-widest">Natural language AI Orchestration layer</p>
        </div>
      </div>

      <div className="flex-1 rounded border border-border bg-panel flex flex-col overflow-hidden">
        
        {/* Terminal Header */}
        <div className="px-4 py-2 bg-[#14161a] border-b border-border flex items-center space-x-2">
          <div className="flex space-x-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-semantic-red" />
            <div className="w-2.5 h-2.5 rounded-full bg-semantic-amber" />
            <div className="w-2.5 h-2.5 rounded-full bg-semantic-green" />
          </div>
          <div className="flex-1 text-center text-[10px] font-mono text-text-muted tracking-widest uppercase">
            bash - strands_agent
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((message) => (
            <div key={message.id} className={`flex items-start space-x-4 ${message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}>
              
              {/* Avatar */}
              <div className={`shrink-0 w-8 h-8 rounded border flex items-center justify-center ${message.role === 'agent' ? 'bg-semantic-blue/10 border-semantic-blue/30 text-semantic-blue' : 'bg-card border-border text-text-secondary'}`}>
                {message.role === 'agent' ? <Bot className="h-4 w-4" /> : <div className="h-4 w-4 rounded-full bg-text-secondary" />}
              </div>
              
              <div className={`max-w-3xl ${message.role === 'user' ? 'text-right' : 'text-left'}`}>
                <div className={`inline-block p-4 rounded border ${message.role === 'user' ? 'bg-card border-border text-text-primary' : 'bg-[#14161a] border-border text-text-primary shadow-sm'}`}>
                  {message.isThinking ? (
                    <div className="flex space-x-2 items-center h-5">
                      <div className="w-1.5 h-1.5 rounded-full bg-semantic-blue animate-bounce" />
                      <div className="w-1.5 h-1.5 rounded-full bg-semantic-blue animate-bounce" style={{ animationDelay: '0.2s' }} />
                      <div className="w-1.5 h-1.5 rounded-full bg-semantic-blue animate-bounce" style={{ animationDelay: '0.4s' }} />
                    </div>
                  ) : (
                    <p className="whitespace-pre-wrap text-sm font-mono leading-relaxed">{message.content}</p>
                  )}
                </div>

                {/* Tools Used Banner */}
                {message.tools && message.tools.length > 0 && (
                  <div className={`mt-2 flex flex-wrap gap-2 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    {message.tools.map((tool, idx) => (
                      <span key={idx} className="flex items-center px-2 py-1 bg-semantic-amber/10 text-semantic-amber border border-semantic-amber/20 text-[10px] rounded font-mono uppercase tracking-widest">
                        <Wrench className="h-3 w-3 mr-1" />
                        {tool}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
        
        {/* Input Area */}
        <div className="p-4 border-t border-border bg-panel">
          <form onSubmit={handleSend} className="relative flex items-center">
            <span className="absolute left-4 font-mono text-semantic-green select-none">$&gt;</span>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about inventory, recovery, or historical performance..."
              className="w-full pl-10 pr-12 py-3 bg-card border border-border text-text-primary font-mono text-sm rounded focus:outline-none focus:border-semantic-blue transition-colors placeholder-text-muted"
              disabled={isTyping}
            />
            <button
              type="submit"
              disabled={isTyping || !input.trim()}
              className="absolute right-2 top-1.5 bottom-1.5 px-3 bg-semantic-blue text-white rounded hover:bg-semantic-blue/90 disabled:opacity-50 transition-colors flex items-center justify-center"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>

      </div>
    </div>
  );
};
