import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";

export const metadata = {
  title: "Privacy Policy — AWT Cloud",
};

export default async function PrivacyPage() {
  const locale = await getLocale();
  const t = await getTranslations("privacy");

  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="mb-2 text-3xl font-bold text-gray-900">{t("pageTitle")}</h1>
      <p className="mb-8 text-sm text-gray-500">{t("lastUpdated")}</p>
      <div className="prose prose-gray max-w-none text-gray-700 [&_h2]:mt-8 [&_h2]:mb-3 [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:text-gray-900 [&_h3]:mt-6 [&_h3]:mb-2 [&_h3]:text-lg [&_h3]:font-medium [&_h3]:text-gray-800 [&_p]:mb-3 [&_p]:leading-relaxed [&_ul]:mb-3 [&_ul]:list-disc [&_ul]:pl-6 [&_li]:mb-1">
        {locale === "ko" ? <PrivacyContentKo /> : <PrivacyContentEn />}
      </div>
      <div className="mt-8 border-t border-gray-200 pt-6">
        <p className="text-sm text-gray-500">
          {t("seeAlso")}{" "}
          <Link href="/terms" className="text-blue-600 hover:underline">
            {t("termsLink")}
          </Link>
        </p>
      </div>
    </div>
  );
}

function PrivacyContentEn() {
  return (
    <>
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
    </>
  );
}

function PrivacyContentKo() {
  return (
    <>
      <h2>1. 개요</h2>
      <p>
        AWT Cloud(이하 &quot;본 서비스&quot;)는 AWT(이하 &quot;당사&quot;)가 운영합니다.
        본 개인정보 처리방침은 당사가 수집하는 데이터의 종류, 이용 방법 및 귀하의 데이터에 관한 권리를 설명합니다.
      </p>

      <h2>2. 수집하는 데이터</h2>
      <h3>2.1 계정 정보</h3>
      <ul>
        <li>이메일 주소 (인증 및 알림 발송 목적)</li>
        <li>인증 토큰 (Supabase Auth를 통해 관리)</li>
        <li>구독 등급 및 결제 상태</li>
      </ul>

      <h3>2.2 테스트 데이터</h3>
      <ul>
        <li>테스트 대상으로 제출한 URL</li>
        <li>AI가 생성한 테스트 시나리오 (YAML)</li>
        <li>테스트 실행 결과 및 스크린샷</li>
        <li>업로드한 참고 문서 (PDF, DOCX, MD, TXT)</li>
        <li>테스트 실행 중 수집된 콘솔 로그</li>
      </ul>

      <h3>2.3 AI API 키 (BYOK)</h3>
      <p>
        귀하가 직접 AI API 키를 제공하는 경우, 해당 키는
        <strong> Fernet 대칭 암호화</strong>(AES-128-CBC with HMAC-SHA256) 방식으로
        암호화된 후 당사 데이터베이스에 저장됩니다. 암호화 키는 서버 환경 변수로 보관되며,
        클라이언트에 노출되거나 API 응답에 포함되지 않습니다.
        귀하의 키는 당사가 귀하를 대신하여 AI API를 호출할 때 서버 측에서만 복호화됩니다.
      </p>

      <h3>2.4 이용 데이터</h3>
      <ul>
        <li>API 요청 로그 (IP 주소, 타임스탬프, 엔드포인트)</li>
        <li>테스트 실행 횟수 및 소요 시간</li>
        <li>디버깅 및 서비스 개선을 위한 오류 로그</li>
      </ul>

      <h2>3. 데이터 이용 방법</h2>
      <ul>
        <li><strong>서비스 제공:</strong> 테스트 실행, 시나리오 생성, 결과 리포트 생성</li>
        <li><strong>인증:</strong> 본인 확인 및 세션 관리</li>
        <li><strong>과금:</strong> 플랜 한도 대비 사용량 추적</li>
        <li><strong>서비스 개선:</strong> 이용 패턴 분석 및 버그 수정</li>
        <li><strong>커뮤니케이션:</strong> 서비스 관련 알림 발송</li>
      </ul>

      <h2>4. 데이터 저장 및 보안</h2>
      <ul>
        <li><strong>데이터베이스:</strong> Supabase에 호스팅된 PostgreSQL (AWS ap-northeast-2, 서울 리전)</li>
        <li><strong>백엔드:</strong> Render에 호스팅, 전송 중 HTTPS 암호화 적용</li>
        <li><strong>프론트엔드:</strong> Vercel에 호스팅, 글로벌 CDN 제공</li>
        <li><strong>스크린샷:</strong> 백엔드 서버에 임시 저장되며 7일 후 자동 삭제</li>
        <li><strong>API 키:</strong> 저장 시 Fernet 암호화 적용 (2.3항 참조)</li>
      </ul>
      <p>
        모든 데이터는 HTTPS/TLS를 통해 전송됩니다. 당사는 업계 표준 보안 관행을 따르나,
        완전한 보안을 보장하지는 않습니다.
      </p>

      <h2>5. 제3자 서비스</h2>
      <p>당사는 귀하의 데이터를 처리할 수 있는 다음 제3자 서비스를 이용합니다.</p>
      <ul>
        <li><strong>Supabase</strong> — 인증 및 데이터베이스 호스팅</li>
        <li><strong>Render</strong> — 백엔드 애플리케이션 호스팅</li>
        <li><strong>Vercel</strong> — 프론트엔드 호스팅</li>
        <li><strong>Lemon Squeezy</strong> — 결제 처리 (유료 플랜에 한함)</li>
        <li><strong>OpenAI / Anthropic</strong> — AI 시나리오 생성 (서버 기본값 또는 귀하의 BYOK 키 사용)</li>
        <li><strong>Sentry</strong> — 오류 추적 (설정된 경우 선택적 적용)</li>
      </ul>
      <p>
        서버 기본 AI 프로바이더를 사용하는 경우, 테스트 URL 및 페이지 콘텐츠가 시나리오 생성을 위해
        해당 AI 프로바이더로 전송됩니다. BYOK를 사용하는 경우에도 동일한 데이터가 귀하의 API 키를 통해 전송됩니다.
      </p>

      <h2>6. 데이터 보존 기간</h2>
      <ul>
        <li><strong>테스트 결과:</strong> 귀하가 삭제하거나 계정을 해지할 때까지 보존</li>
        <li><strong>스크린샷:</strong> 7일 후 자동 삭제</li>
        <li><strong>업로드 문서:</strong> 귀하가 삭제할 때까지 보존</li>
        <li><strong>계정 데이터:</strong> 계정 해지 후 30일 이내 삭제</li>
        <li><strong>서버 로그:</strong> 최대 30일간 보존</li>
      </ul>

      <h2>7. 귀하의 권리</h2>
      <p>귀하는 다음과 같은 권리를 가집니다.</p>
      <ul>
        <li><strong>열람:</strong> 대시보드 및 API를 통해 본인 데이터 조회</li>
        <li><strong>삭제:</strong> 테스트 데이터, 문서 및 API 키를 언제든지 삭제</li>
        <li><strong>내보내기:</strong> 테스트 시나리오(YAML) 및 결과(JSON) 다운로드</li>
        <li><strong>계정 해지:</strong> 계정 해지 및 전체 데이터 삭제 요청</li>
        <li><strong>키 철회:</strong> 설정 메뉴에서 언제든지 BYOK API 키 제거</li>
      </ul>

      <h2>8. 쿠키</h2>
      <p>
        당사는 인증(Supabase 세션 토큰)을 위한 필수 쿠키 및 로컬 스토리지만 사용합니다.
        추적 쿠키 또는 제3자 분석 쿠키는 사용하지 않습니다.
      </p>

      <h2>9. 아동 개인정보 보호</h2>
      <p>
        본 서비스는 만 16세 미만 사용자를 대상으로 하지 않습니다.
        당사는 아동으로부터 고의로 데이터를 수집하지 않습니다.
      </p>

      <h2>10. 방침 변경</h2>
      <p>
        당사는 본 개인정보 처리방침을 수시로 업데이트할 수 있습니다. 중요한 변경 사항은
        이메일 또는 앱 내 알림을 통해 고지합니다. 상단의 &quot;최종 업데이트&quot; 날짜는
        가장 최근의 개정일을 나타냅니다.
      </p>

      <h2>11. 문의</h2>
      <p>
        개인정보 관련 문의 또는 데이터 삭제 요청은{" "}
        <a href="mailto:awt.dev.team@gmail.com" className="text-blue-600 hover:underline">awt.dev.team@gmail.com</a>
        으로 연락해 주시기 바랍니다.
      </p>
    </>
  );
}
