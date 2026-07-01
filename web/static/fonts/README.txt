Coloque aqui o arquivo self-hosted da fonte:

    RobotoFlex.woff2

Baixe o Roboto Flex (variavel) em https://fonts.google.com/specimen/Roboto+Flex
e converta/renomeie para RobotoFlex.woff2. O @font-face esta em
/css/tokens.css e o carregamento e "font-display: swap".

Se o arquivo nao existir, a interface usa a pilha de fontes do sistema
(system-ui) automaticamente — nada quebra. Nenhuma fonte e carregada de
terceiros em runtime (requisito de privacidade/CSP).
