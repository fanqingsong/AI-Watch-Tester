import Link from "next/link";

export const metadata = {
  title: "Privacy Policy — AWT Cloud",
};

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="mb-2 text-3xl font-bold text-gray-900">Privacy Policy</h1>
      <p className="mb-8 text-sm text-gray-500">Last updated: February 24, 2026</p>

      <div className="prose prose-gray max-w-none text-gray-700 [&_h2]:mt-8 [&_h2]:mb-3 [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:text-gray-900 [&_h3]:mt-6 [&_h3]:mb-2 [&_h3]:text-lg [&_h3]:font-medium [&_h3]:text-gray-800 [&_p]:mb-3 [&_p]:leading-relaxed [&_ul]:mb-3 [&_ul]:list-disc [&_ul]:pl-6 [&_li]:mb-1">
        <h2>1. Overview</h2>
        <p>
          AWT Cloud (&quot;the Service&quot;) is operated by AWT (&quot;we&quot;, &quot;us&quot;, or &quot;our&quot;).
          This Privacy Policy explains what data we collect, how we use it, and your rights regarding your data.
        </p>

        <h2>2. Data We Collect</h2>
        <h3>2.1 Account Information</h3>
        <ul>
          <li>Email address (used for authentication and notifications)</li>
          <li>Authentication tokens (managed by Supabase Auth)</li>
          <li>Subscription tier and billing status</li>
        </ul>

        <h3>2.2 Test Data</h3>
        <ul>
          <li>Target URLs you submit for testing</li>
          <li>AI-generated test scenarios (YAML)</li>
          <li>Test execution results and screenshots</li>
          <li>Uploaded reference documents (PDF, DOCX, MD, TXT)</li>
          <li>Console logs captured during test execution</li>
        </ul>

        <h3>2.3 AI API Keys (BYOK)</h3>
        <p>
          If you choose to provide your own AI API key, it is encrypted using
          <strong> Fernet symmetric encryption</strong> (AES-128-CBC with HMAC-SHA256)
          before being stored in our database. The encryption key is stored as a server
          environment variable and is never exposed to clients or included in API responses.
          We only decrypt your key server-side when making AI API calls on your behalf.
        </p>

        <h3>2.4 Usage Data</h3>
        <ul>
          <li>API request logs (IP address, timestamp, endpoint)</li>
          <li>Test execution counts and timing</li>
          <li>Error logs for debugging and service improvement</li>
        </ul>

        <h2>3. How We Use Your Data</h2>
        <ul>
          <li><strong>Service delivery:</strong> Running tests, generating scenarios, producing reports</li>
          <li><strong>Authentication:</strong> Verifying your identity and managing sessions</li>
          <li><strong>Billing:</strong> Tracking usage against plan limits</li>
          <li><strong>Service improvement:</strong> Analyzing usage patterns and fixing bugs</li>
          <li><strong>Communication:</strong> Sending service-related notifications</li>
        </ul>

        <h2>4. Data Storage and Security</h2>
        <ul>
          <li><strong>Database:</strong> PostgreSQL hosted on Supabase (AWS ap-northeast-2, Seoul region)</li>
          <li><strong>Backend:</strong> Hosted on Render with HTTPS encryption in transit</li>
          <li><strong>Frontend:</strong> Hosted on Vercel with global CDN</li>
          <li><strong>Screenshots:</strong> Stored temporarily on the backend server; deleted after 7 days</li>
          <li><strong>API keys:</strong> Fernet-encrypted at rest (see Section 2.3)</li>
        </ul>
        <p>
          All data is transmitted over HTTPS/TLS. We use industry-standard security practices
          but cannot guarantee absolute security.
        </p>

        <h2>5. Third-Party Services</h2>
        <p>We use the following third-party services that may process your data:</p>
        <ul>
          <li><strong>Supabase</strong> — Authentication and database hosting</li>
          <li><strong>Render</strong> — Backend application hosting</li>
          <li><strong>Vercel</strong> — Frontend hosting</li>
          <li><strong>Lemon Squeezy</strong> — Payment processing (paid plans only)</li>
          <li><strong>OpenAI / Anthropic</strong> — AI scenario generation (server default or your BYOK key)</li>
          <li><strong>Sentry</strong> — Error tracking (optional, if configured)</li>
        </ul>
        <p>
          When using the server default AI provider, test URLs and page content are sent to the
          AI provider for scenario generation. When using BYOK, the same data is sent using your own API key.
        </p>

        <h2>6. Data Retention</h2>
        <ul>
          <li><strong>Test results:</strong> Retained until you delete them or close your account</li>
          <li><strong>Screenshots:</strong> Automatically deleted after 7 days</li>
          <li><strong>Uploaded documents:</strong> Retained until you delete them</li>
          <li><strong>Account data:</strong> Deleted within 30 days of account closure</li>
          <li><strong>Server logs:</strong> Retained for up to 30 days</li>
        </ul>

        <h2>7. Your Rights</h2>
        <p>You have the right to:</p>
        <ul>
          <li><strong>Access</strong> your data through the dashboard and API</li>
          <li><strong>Delete</strong> your test data, documents, and API keys at any time</li>
          <li><strong>Export</strong> your test scenarios (YAML) and results (JSON)</li>
          <li><strong>Close</strong> your account and request full data deletion</li>
          <li><strong>Withdraw</strong> your BYOK API key at any time via Settings</li>
        </ul>

        <h2>8. Cookies</h2>
        <p>
          We use essential cookies and local storage for authentication (Supabase session tokens).
          We do not use tracking cookies or third-party analytics cookies.
        </p>

        <h2>9. Children&apos;s Privacy</h2>
        <p>
          The Service is not intended for users under 16 years of age.
          We do not knowingly collect data from children.
        </p>

        <h2>10. Changes to This Policy</h2>
        <p>
          We may update this Privacy Policy from time to time. Material changes will be communicated
          via email or in-app notification. The &quot;Last updated&quot; date at the top indicates the latest revision.
        </p>

        <h2>11. Contact</h2>
        <p>
          For privacy-related questions or data deletion requests, contact us at{" "}
          <a href="mailto:awt.dev.team@gmail.com" className="text-blue-600 hover:underline">awt.dev.team@gmail.com</a>.
        </p>
      </div>

      <div className="mt-8 border-t border-gray-200 pt-6">
        <p className="text-sm text-gray-500">
          See also: <Link href="/terms" className="text-blue-600 hover:underline">Terms of Service</Link>
        </p>
      </div>
    </div>
  );
}
