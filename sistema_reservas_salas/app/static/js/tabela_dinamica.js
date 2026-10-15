// app/static/js/tabela_dinamica.js
document.addEventListener("DOMContentLoaded", () => {
    let temporizadorDebounce = null;
    const pedidosEmAndamento = {};  // um pedido por tabela: { "#container-tabela-salas": AbortController }

    function mostrarErro(container, mensagem) {
        container.innerHTML = `<div class="p-8 text-center text-sm text-rose-700">${mensagem}</div>`;
    }

    function carregarTabelaDinamica(form, pagina = 1) {
        const seletorAlvo = form.dataset.target || "#container-tabela";
        const container = document.querySelector(seletorAlvo);
        if (!container) return;

        // Parte da URL atual para preservar filtros e páginas de outras tabelas na mesma tela
        const url = new URL(window.location.href);
        if (form.action) {
            url.pathname = new URL(form.action, window.location.origin).pathname;
        }

        const dadosForm = new FormData(form);
        dadosForm.forEach((valor, chave) => {
            if (valor !== "") {
                url.searchParams.set(chave, valor);
            } else {
                url.searchParams.delete(chave);
            }
        });

        // Permite definir um parâmetro de página exclusivo por tabela (ex: data-page-param="page_salas")
        const paramPagina = form.dataset.pageParam || "page";
        url.searchParams.set(paramPagina, pagina);

        // Cancela o pedido anterior DESTA tabela, se ainda estiver a caminho
        if (pedidosEmAndamento[seletorAlvo]) {
            pedidosEmAndamento[seletorAlvo].abort();
        }
        const controlador = new AbortController();
        pedidosEmAndamento[seletorAlvo] = controlador;

        container.classList.add("opacity-60", "transition-opacity");

        fetch(url.toString(), {
            headers: { "X-Requested-With": "XMLHttpRequest" },
            signal: controlador.signal
        })
        .then((resposta) => {
            // Sessão expirada: recarrega a página inteira para o servidor mandar para o login
            if (resposta.status === 401 || resposta.redirected) {
                window.location.reload();
                return null;
            }
            if (!resposta.ok) {
                throw new Error("Resposta com erro: " + resposta.status);
            }
            return resposta.text();
        })
        .then((html) => {
            if (html === null) return;
            const docTemp = new DOMParser().parseFromString(html, "text/html");
            const novoConteudo = docTemp.querySelector(seletorAlvo);
            if (!novoConteudo) {
                throw new Error("A resposta não trouxe o container esperado");
            }
            container.innerHTML = novoConteudo.innerHTML;
            window.history.replaceState({}, "", url.toString());
        })
        .catch((erro) => {
            if (erro.name === "AbortError") return;  // pedido cancelado de propósito: não é erro
            mostrarErro(container, "Não foi possível atualizar a tabela. Recarregue a página e tente novamente.");
        })
        .finally(() => {
            if (pedidosEmAndamento[seletorAlvo] === controlador) {
                container.classList.remove("opacity-60");
            }
        });
    }

    // 1. Escuta digitação nos campos de busca dinâmica com Debounce de 300ms
    document.body.addEventListener("input", (evento) => {
        if (evento.target.matches(".js-busca-dinamica")) {
            const form = evento.target.closest(".js-form-filtro");
            clearTimeout(temporizadorDebounce);
            temporizadorDebounce = setTimeout(() => {
                carregarTabelaDinamica(form, 1);
            }, 300);
        }
    });

    // 2. Escuta mudança em selects/filtros de data ou itens por página
    document.body.addEventListener("change", (evento) => {
        if (evento.target.matches(".js-filtro-imediato")) {
            const form = evento.target.closest(".js-form-filtro");
            carregarTabelaDinamica(form, 1);
        }
    });

    // 3. Escuta cliques nos botões de paginação
    document.body.addEventListener("click", (evento) => {
        const botaoPagina = evento.target.closest(".js-btn-pagina");
        if (botaoPagina && !botaoPagina.disabled) {
            evento.preventDefault();
            const seletorAlvo = botaoPagina.dataset.target || "#container-tabela";
            const form = document.querySelector(`.js-form-filtro[data-target="${seletorAlvo}"]`)
                      || document.querySelector(".js-form-filtro");
            if (form) {
                carregarTabelaDinamica(form, botaoPagina.dataset.page);
            }
        }
    });

    // 4. Tecla Enter dentro do formulário de filtros: busca dinâmica em vez de recarregar a página
    document.body.addEventListener("submit", (evento) => {
        const form = evento.target;
        if (form.matches(".js-form-filtro")) {
            evento.preventDefault();
            clearTimeout(temporizadorDebounce);
            carregarTabelaDinamica(form, 1);
        }
    });
    // 5. Botões de ação (exportar CSV, imprimir) que levam os filtros ATUAIS do formulário
    document.body.addEventListener("click", (evento) => {
        const botao = evento.target.closest(".js-acao-com-filtros");
        if (!botao) return;

        const form = botao.closest(".js-form-filtro");
        if (!form) return;

        const destino = new URL(botao.dataset.url, window.location.origin);
        new FormData(form).forEach((valor, chave) => {
            if (valor !== "") {
                destino.searchParams.set(chave, valor);
            }
        });

        if (botao.dataset.novaAba === "1") {
            window.open(destino.toString(), "_blank");
        } else {
            window.location.href = destino.toString();
        }
    });
});
