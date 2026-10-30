import React from 'react';
import { X, ShieldCheck, FileText, Database, Scale } from 'lucide-react';

interface PrivacyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PrivacyModal: React.FC<PrivacyModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="privacy-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 overflow-y-auto"
    >
      <div className="relative w-full max-w-2xl bg-white border border-ink-border rounded-lg shadow-xl overflow-hidden my-6 max-h-[90vh] flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-ink-border bg-white">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-md bg-forest-50 border border-forest-200 text-forest-700">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 id="privacy-modal-title" className="text-base font-bold text-ink-primary tracking-tight">
                Privacy Policy &amp; Legal Disclaimers
              </h2>
              <p className="text-xs text-ink-secondary mt-0.5">
                Data handling practices, licensing attribution, and fair-use disclaimers.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close privacy modal"
            className="p-1.5 rounded-md text-ink-secondary hover:text-ink-primary hover:bg-canvas transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto space-y-4 text-xs text-ink-primary bg-canvas">
          {/* Section 1: Privacy & Data Retention */}
          <div className="p-4 rounded-lg bg-white border border-ink-border space-y-2">
            <div className="flex items-center space-x-2 text-forest-700 font-semibold">
              <Database className="w-4 h-4" />
              <h3 className="text-xs font-semibold text-ink-primary">1. Privacy &amp; Data Collection</h3>
            </div>
            <p className="text-ink-secondary leading-relaxed">
              BoundaryIQ is designed with privacy-by-default architecture. We do not store, track, sell, or collect personal identifying information (PII). All user-configured fantasy squads, custom multiplier selections, and replay seek positions exist solely in browser session memory.
            </p>
          </div>

          {/* Section 2: Data Attribution & Licensing */}
          <div className="p-4 rounded-lg bg-white border border-ink-border space-y-2">
            <div className="flex items-center space-x-2 text-forest-700 font-semibold">
              <FileText className="w-4 h-4" />
              <h3 className="text-xs font-semibold text-ink-primary">2. Open Data Licensing (Cricsheet ODC-BY 1.0)</h3>
            </div>
            <p className="text-ink-secondary leading-relaxed">
              Ball-by-ball cricket match event data utilized by BoundaryIQ is sourced from{' '}
              <a
                href="https://cricsheet.org"
                target="_blank"
                rel="noreferrer"
                className="text-forest-700 underline font-medium hover:text-forest-800"
              >
                Cricsheet.org
              </a>{' '}
              and is licensed under the{' '}
              <strong>Open Data Commons Attribution License (ODC-BY 1.0)</strong>. You are free to share, modify, and produce works from this data provided appropriate credit is given.
            </p>
          </div>

          {/* Section 3: Nominative Fair Use & Non-Affiliation */}
          <div className="p-4 rounded-lg bg-white border border-ink-border space-y-2">
            <div className="flex items-center space-x-2 text-forest-700 font-semibold">
              <Scale className="w-4 h-4" />
              <h3 className="text-xs font-semibold text-ink-primary">3. Non-Affiliation &amp; Trademark Disclaimers</h3>
            </div>
            <p className="text-ink-secondary leading-relaxed">
              BoundaryIQ is an independent sports analytics demonstration and educational platform. It is <strong>NOT</strong> affiliated with, associated with, authorized by, endorsed by, or in any way officially connected with:
            </p>
            <ul className="list-disc pl-5 space-y-1 text-ink-secondary">
              <li><strong>Dream11</strong> or Sporta Technologies Pvt. Ltd.</li>
              <li>The <strong>International Cricket Council (ICC)</strong></li>
              <li>The <strong>Board of Control for Cricket in India (BCCI)</strong></li>
              <li><strong>Cricket South Africa (CSA)</strong></li>
            </ul>
            <p className="text-ink-secondary leading-relaxed">
              All player names, tournament names, and trademarks are property of their respective owners and are referenced here under nominative fair use for descriptive, analytical, and informational demonstration purposes only.
            </p>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-end px-6 py-3 border-t border-ink-border bg-white">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-md bg-forest-600 text-white font-medium text-xs hover:bg-forest-700 transition-colors"
          >
            I Understand
          </button>
        </div>
      </div>
    </div>
  );
};

