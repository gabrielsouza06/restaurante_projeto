from abc import ABC, abstractmethod


class Funcionario(ABC):
    """Classe abstrata base para toda a equipe do restaurante."""

    def __init__(self, matricula: int, nome: str, turno: str = "Integral"):
        if not nome or not nome.strip():
            raise ValueError("O nome do funcionário é obrigatório.")
        self.matricula = matricula
        self.nome = nome.strip()
        self.turno = turno

    @property
    @abstractmethod
    def cargo(self) -> str:
        """Retorna o nome oficial do cargo."""

    @abstractmethod
    def descrever_funcao(self) -> str:
        """Descreve as responsabilidades principais do cargo."""

    def registrar_ponto(self) -> str:
        return f"[{self.cargo}] {self.nome} (Matrícula #{self.matricula}) — Turno: {self.turno}"

    def __str__(self) -> str:
        return f"{self.nome} ({self.cargo})"


class GerenteGeneral(Funcionario):
    @property
    def cargo(self) -> str:
        return "Gerente Geral"

    def descrever_funcao(self) -> str:
        return "Supervisiona o salão, aprova exceções, emite relatórios gerenciais e aciona o manobrista."

    def emitir_ordem_manobrista(
        self,
        manobrista: "Manobrista",
        cliente_nome: str,
        nota_id: int,
        placa_veiculo: str = "",
    ) -> str:
        detalhe_placa = f" (Placa: {placa_veiculo.strip().upper()})" if placa_veiculo and placa_veiculo.strip() else ""
        return (
            f"Ordem de {self.nome} para {manobrista.nome}: "
            f"Colocar carro do cliente {cliente_nome} na portaria{detalhe_placa} — Nota #{nota_id} quitada."
        )


GerenteGeral = GerenteGeneral


class ChefeCozinha(Funcionario):
    @property
    def cargo(self) -> str:
        return "Chefe de Cozinha"

    def descrever_funcao(self) -> str:
        return "Coordena o preparo dos pratos, controla o tempo de cozinha e avalia devoluções culinárias."


class GarcomChefe(Funcionario):
    def __init__(self, matricula: int, nome: str, regiao_supervisionada: str = "Salão Principal", turno: str = "Integral"):
        super().__init__(matricula, nome, turno)
        self.regiao_supervisionada = regiao_supervisionada

    @property
    def cargo(self) -> str:
        return "Garçom-Chefe"

    def descrever_funcao(self) -> str:
        return f"Coordena os garçons e a distribuição de mesas na região '{self.regiao_supervisionada}'."


class Garcom(Funcionario):
    def __init__(self, matricula: int, nome: str, mesas_atendidas: list[int] | None = None, turno: str = "Integral"):
        super().__init__(matricula, nome, turno)
        self.mesas_atendidas = mesas_atendidas or []

    @property
    def cargo(self) -> str:
        return "Garçom"

    def descrever_funcao(self) -> str:
        mesas = ", ".join(str(m) for m in self.mesas_atendidas) or "sob demanda"
        return f"Atende clientes no salão, registra pedidos e acompanha mesas ({mesas})."


class GarcomBebida(Funcionario):
    @property
    def cargo(self) -> str:
        return "Garçom de Bebidas"

    def descrever_funcao(self) -> str:
        return "Gerencia o serviço de bebidas e verifica se todo pedido com prato possui bebida acompanhando."


class Telefonista(Funcionario):
    @property
    def cargo(self) -> str:
        return "Telefonista"

    def descrever_funcao(self) -> str:
        return "Registra pedidos remotos/delivery, agendamentos e encaminha rotas de entrega."


class Manobrista(Funcionario):
    @property
    def cargo(self) -> str:
        return "Manobrista"

    def descrever_funcao(self) -> str:
        return "Recepciona veículos na chegada e traz o carro do cliente à portaria após ordem do gerente."


class Seguranca(Funcionario):
    @property
    def cargo(self) -> str:
        return "Segurança"

    def descrever_funcao(self) -> str:
        return "Controla o acesso ao restaurante, salão e área externa de embarque/desembarque."