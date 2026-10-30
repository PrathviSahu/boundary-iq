import React, { useState } from 'react';
import { X, MessageSquare, Send, CheckCircle2, User, Mail, Tag } from 'lucide-react';

interface ContactModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ContactModal: React.FC<ContactModalProps> = ({ isOpen, onClose }) => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [category, setCategory] = useState('Recruiter / Hiring Manager');
  const [message, setMessage] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    // Simulate real feedback persistence & receipt generation
    setTimeout(() => {
      setSubmitting(false);
      setSubmitted(true);
    }, 400);
  };

  const handleReset = () => {
    setName('');
    setEmail('');
    setMessage('');
    setSubmitted(false);
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="contact-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 overflow-y-auto"
    >
      <div className="relative w-full max-w-lg bg-white border border-ink-border rounded-lg shadow-xl overflow-hidden my-6 flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-ink-border bg-white">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-md bg-forest-50 border border-forest-200 text-forest-700">
              <MessageSquare className="w-5 h-5" />
            </div>
            <div>
              <h2 id="contact-modal-title" className="text-base font-bold text-ink-primary tracking-tight">
                Feedback &amp; Developer Contact
              </h2>
              <p className="text-xs text-ink-secondary mt-0.5">
                Share feedback, audit findings, or connect with the engineering team.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close contact dialog"
            className="p-1.5 rounded-md text-ink-secondary hover:text-ink-primary hover:bg-canvas transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 bg-canvas">
          {submitted ? (
            <div className="text-center py-6 space-y-3 bg-white p-6 rounded-lg border border-ink-border">
              <div className="w-12 h-12 bg-forest-100 text-forest-700 rounded-full flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-bold text-ink-primary">Feedback Dispatched Successfully</h3>
              <p className="text-xs text-ink-secondary leading-relaxed">
                Thank you, <strong>{name || 'Contributor'}</strong>! Your message has been logged. We appreciate you taking the time to review BoundaryIQ.
              </p>
              <div className="pt-2">
                <button
                  onClick={handleReset}
                  className="px-4 py-2 rounded-md bg-forest-600 text-white font-medium text-xs hover:bg-forest-700 transition-colors"
                >
                  Done
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Name */}
              <div>
                <label className="block text-xs font-semibold text-ink-primary mb-1">
                  Full Name <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <User className="w-3.5 h-3.5 text-ink-muted absolute left-3 top-2.5" />
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Alex Sharma"
                    className="w-full pl-9 pr-3 py-2 text-xs border border-ink-border rounded-md bg-white text-ink-primary focus:outline-none focus:border-forest-500 focus:ring-1 focus:ring-forest-500"
                  />
                </div>
              </div>

              {/* Email / Profile */}
              <div>
                <label className="block text-xs font-semibold text-ink-primary mb-1">
                  Email or LinkedIn / GitHub Profile <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <Mail className="w-3.5 h-3.5 text-ink-muted absolute left-3 top-2.5" />
                  <input
                    type="text"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="alex@company.com or linkedin.com/in/alex"
                    className="w-full pl-9 pr-3 py-2 text-xs border border-ink-border rounded-md bg-white text-ink-primary focus:outline-none focus:border-forest-500 focus:ring-1 focus:ring-forest-500"
                  />
                </div>
              </div>

              {/* Category */}
              <div>
                <label className="block text-xs font-semibold text-ink-primary mb-1">
                  Purpose / Role
                </label>
                <div className="relative">
                  <Tag className="w-3.5 h-3.5 text-ink-muted absolute left-3 top-2.5" />
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 text-xs border border-ink-border rounded-md bg-white text-ink-primary focus:outline-none focus:border-forest-500 focus:ring-1 focus:ring-forest-500"
                  >
                    <option value="Recruiter / Hiring Manager">Recruiter / Hiring Manager</option>
                    <option value="QA / Engineering Reviewer">QA / Engineering Reviewer</option>
                    <option value="Sports Analytics Enthusiast">Sports Analytics Enthusiast</option>
                    <option value="Feature Suggestion">Feature Suggestion</option>
                    <option value="Bug Report">Bug Report</option>
                  </select>
                </div>
              </div>

              {/* Message */}
              <div>
                <label className="block text-xs font-semibold text-ink-primary mb-1">
                  Message / Feedback Notes <span className="text-red-500">*</span>
                </label>
                <textarea
                  required
                  rows={4}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Share impressions on the UI, fantasy calculations, AI match explainers, or architecture..."
                  className="w-full p-2.5 text-xs border border-ink-border rounded-md bg-white text-ink-primary focus:outline-none focus:border-forest-500 focus:ring-1 focus:ring-forest-500 resize-none"
                />
              </div>

              {/* Submit Button */}
              <div className="flex items-center justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-3.5 py-2 text-xs rounded-md border border-ink-border text-ink-secondary hover:text-ink-primary bg-white hover:bg-canvas transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-md bg-forest-600 text-white font-medium text-xs hover:bg-forest-700 transition-colors disabled:opacity-60"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>{submitting ? 'Sending...' : 'Submit Feedback'}</span>
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

