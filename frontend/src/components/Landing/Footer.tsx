import { Link } from "react-router-dom";

function GitHubIcon() {
  return (
    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fillRule="evenodd"
        d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.49.5.092.682-.217.682-.482 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function TwitterIcon() {
  return (
    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M23 3a10.9 10.9 0 01-3.14 1.53 4.48 4.48 0 01-8.86 3c-1.29-.56-2.44-1.5-3.17-2.45a12.59 12.59 0 00-1.86 6.18c0 .01-.01.02-.01.03A4.47 4.47 0 001.67 18a4.48 4.48 0 004.47 4.47 4.49 4.49 0 004.47-4.47c0-.36-.03-.72-.08-1.06A12.5 12.5 0 0012 5.82a12.8 12.8 0 014.66-1.59c.66-.09 1.31-.14 1.95-.14.55 0 1.1.05 1.63.14C22.57 5.92 24 7.58 24 9.41c0 2.81-1.96 5.25-4.58 5.65l-.03.2-.03-.2c1.66-.36 3-1.86 3.55-3.72.09-.35.14-.73.14-1.12 0-2.31-1.44-4.37-3.57-5.1a4.51 4.51 0 00-2.03-.66c-.72 0-1.4.16-2.04.45 2.56 1.65 5.58 2.77 8.92 2.85-5.46-2.06-8.88-6.88-8.88-12.15 0-2.69 1.33-5.07 3.5-6.36a4.48 4.48 0 014.47-4.47c1.25 0 2.41.4 3.35 1.14.53-.17 1.03-.36 1.54-.58-.17.55-.36 1.1-.46 1.67a8.14 8.14 0 01-2.43 2.25c-.21.02-.42.03-.63.03 0 .22 0 .45-.01.67a15.2 15.2 0 017.19-3.82 4.5 4.5 0 00-.91-1.55 4.5 4.5 0 00-3.4 1.58 4.51 4.51 0 012.9-.83 4.5 4.5 0 00-1.22 4.77 4.5 4.5 0 004.46 4.5c3.39 0 5.25-2.81 5.25-6.26 0-.39-.01-.78-.03-1.17A11.6 11.6 0 0024 3.09a9.55 9.55 0 00-1-.31z" />
    </svg>
  );
}

function LinkedInIcon() {
  return (
    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fillRule="evenodd"
        d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"
        clipRule="evenodd"
      />
    </svg>
  );
}

const footerLinks = {
  Produto: [
    { label: "Cardápio Digital", href: "#" },
    { label: "KDS + Comanda", href: "#" },
    { label: "Estoque + Fichas", href: "#" },
    { label: "Compras Inteligentes", href: "#" },
    { label: "Preços", href: "/register" },
  ],
  Empresa: [
    { label: "Sobre nós", href: "#" },
    { label: "Blog", href: "#" },
    { label: "Carreiras", href: "#" },
    { label: "Imprensa", href: "#" },
    { label: "Contato", href: "#" },
  ],
  Recursos: [
    { label: "Documentação", href: "/docs" },
    { label: "API Reference", href: "/api" },
    { label: "Status", href: "/status" },
    { label: "Changelog", href: "/changelog" },
    { label: "Comunidade", href: "#" },
  ],
  Legal: [
    { label: "Privacidade", href: "#" },
    { label: "Termos de uso", href: "#" },
    { label: "LGPD", href: "#" },
    { label: "Cookies", href: "#" },
    { label: "Segurança", href: "#" },
  ],
};

const socialIcons = [
  {
    key: "github",
    Icon: GitHubIcon,
    href: "https://github.com/clsalbertogx/StockChef",
    label: "GitHub",
  },
  { key: "twitter", Icon: TwitterIcon, href: "https://twitter.com", label: "Twitter" },
  { key: "linkedin", Icon: LinkedInIcon, href: "https://linkedin.com", label: "LinkedIn" },
];

export function Footer() {
  return (
    <footer
      className="bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800"
      role="contentinfo"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 lg:py-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
          <div className="md:col-span-2 lg:col-span-1">
            <Link
              to="/register"
              className="inline-flex items-center gap-2 font-bold text-xl text-blue-600 dark:text-blue-400 mb-4"
              aria-label="StockChef - Ir para registro"
            >
              <svg
                className="h-8 w-8 text-blue-600 dark:text-blue-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              StockChef
            </Link>
            <p className="text-gray-600 dark:text-gray-400 text-sm leading-relaxed mb-6 max-w-xs">
              SaaS de delivery próprio + controle de estoque por ficha técnica. Sem taxas por
              pedido. Controle total do seu restaurante.
            </p>
            <div className="flex gap-4">
              {socialIcons.map((item) => (
                <a
                  key={item.key}
                  href={item.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                  aria-label={item.label}
                >
                  <item.Icon />
                </a>
              ))}
            </div>
          </div>
          {Object.entries(footerLinks).map(([category, links]) => (
            <nav key={category} aria-labelledby={`footer-${category.toLowerCase()}`}>
              <h3
                id={`footer-${category.toLowerCase()}`}
                className="font-semibold text-gray-900 dark:text-white mb-4"
              >
                {category}
              </h3>
              <ul className="space-y-3">
                {links.map((link) => (
                  <li key={link.href}>
                    <Link
                      to={link.href}
                      className="text-sm text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>
        <div className="pt-8 border-t border-gray-200 dark:border-gray-800">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              © {new Date().getFullYear()} StockChef. Todos os direitos reservados.
            </p>
            <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
              <Link to="#" className="hover:text-gray-700 dark:hover:text-gray-300">
                Privacidade
              </Link>
              <Link to="#" className="hover:text-gray-700 dark:hover:text-gray-300">
                Termos
              </Link>
              <Link to="#" className="hover:text-gray-700 dark:hover:text-gray-300">
                LGPD
              </Link>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
