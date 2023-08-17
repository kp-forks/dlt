import inspect
from typing import Any, Optional

import dlt
from dlt.common import Decimal
from dlt.common.typing import TSecretValue, is_optional_type
from dlt.common.configuration.inject import get_fun_spec, with_config
from dlt.common.configuration.specs import BaseConfiguration, RunConfiguration, ConnectionStringCredentials
from dlt.common.reflection.spec import spec_from_signature, _get_spec_name_from_f
from dlt.common.reflection.utils import get_func_def_node, get_literal_defaults


_DECIMAL_DEFAULT = Decimal("0.01")
_SECRET_DEFAULT = TSecretValue("PASS")
_CONFIG_DEFAULT = RunConfiguration()
_CREDENTIALS_DEFAULT = ConnectionStringCredentials("postgresql://loader:loader@localhost:5432/dlt_data")


def test_synthesize_spec_from_sig() -> None:

    # spec from typed signature without defaults

    def f_typed(p1: str = None, p2: Decimal = None, p3: Any = None, p4: Optional[RunConfiguration] = None, p5: TSecretValue = dlt.secrets.value) -> None:
        pass

    SPEC = spec_from_signature(f_typed, inspect.signature(f_typed))
    assert SPEC.p1 is None
    assert SPEC.p2 is None
    assert SPEC.p3 is None
    assert SPEC.p4 is None
    assert SPEC.p5 is None
    fields = SPEC.get_resolvable_fields()
    assert fields == {"p1": Optional[str], "p2": Optional[Decimal], "p3": Optional[Any], "p4": Optional[RunConfiguration], "p5": TSecretValue}

    # spec from typed signatures with defaults

    def f_typed_default(t_p1: str = "str", t_p2: Decimal = _DECIMAL_DEFAULT, t_p3: Any = _SECRET_DEFAULT, t_p4: RunConfiguration = _CONFIG_DEFAULT, t_p5: str = None) -> None:
        pass

    SPEC = spec_from_signature(f_typed_default, inspect.signature(f_typed_default))
    assert SPEC.t_p1 == "str"
    assert SPEC.t_p2 == _DECIMAL_DEFAULT
    assert SPEC.t_p3 == _SECRET_DEFAULT
    assert isinstance(SPEC().t_p4, RunConfiguration)
    assert SPEC.t_p5 is None
    fields = SPEC().get_resolvable_fields()
    # Any will not assume TSecretValue type because at runtime it's a str
    # setting default as None will convert type into optional (t_p5)
    assert fields == {"t_p1": str, "t_p2": Decimal, "t_p3": str, "t_p4": RunConfiguration, "t_p5": Optional[str]}

    # spec from untyped signature

    def f_untyped(untyped_p1 = None, untyped_p2 = dlt.config.value) -> None:
        pass

    SPEC = spec_from_signature(f_untyped, inspect.signature(f_untyped))
    assert SPEC.untyped_p1 is None
    assert SPEC.untyped_p2 is None
    fields = SPEC.get_resolvable_fields()
    assert fields == {"untyped_p1": Optional[Any], "untyped_p2": Any}

    # spec types derived from defaults


    def f_untyped_default(untyped_p1 = "str", untyped_p2 = _DECIMAL_DEFAULT, untyped_p3 = _CREDENTIALS_DEFAULT, untyped_p4 = None) -> None:
        pass


    SPEC = spec_from_signature(f_untyped_default, inspect.signature(f_untyped_default))
    assert SPEC.untyped_p1 == "str"
    assert SPEC.untyped_p2 == _DECIMAL_DEFAULT
    assert isinstance(SPEC().untyped_p3, ConnectionStringCredentials)
    assert SPEC.untyped_p4 is None
    fields = SPEC.get_resolvable_fields()
    # untyped_p4 converted to Optional[Any]
    assert fields == {"untyped_p1": str, "untyped_p2": Decimal, "untyped_p3": ConnectionStringCredentials, "untyped_p4": Optional[Any]}

    # spec from signatures containing positional only and keywords only args

    def f_pos_kw_only(pos_only_1=dlt.config.value, pos_only_2: str = "default", /, *, kw_only_1=None, kw_only_2: int = 2) -> None:
        pass

    SPEC = spec_from_signature(f_pos_kw_only, inspect.signature(f_pos_kw_only))
    assert SPEC.pos_only_1 is None
    assert SPEC.pos_only_2 == "default"
    assert SPEC.kw_only_1 is None
    assert SPEC.kw_only_2 == 2
    fields = SPEC.get_resolvable_fields()
    assert fields == {"pos_only_1": Any, "pos_only_2": str, "kw_only_1": Optional[Any], "kw_only_2": int}

    # skip arguments with defaults
    # deregister spec to disable cache
    del globals()[SPEC.__name__]
    SPEC = spec_from_signature(f_pos_kw_only, inspect.signature(f_pos_kw_only), include_defaults=False)
    assert not hasattr(SPEC, "kw_only_1")
    assert not hasattr(SPEC, "kw_only_2")
    assert not hasattr(SPEC, "pos_only_2")
    assert hasattr(SPEC, "pos_only_1")
    fields = SPEC.get_resolvable_fields()
    assert fields == {"pos_only_1": Any}

    def f_variadic(var_1: str = "A", *args, kw_var_1: str, **kwargs) -> None:
        print(locals())

    SPEC = spec_from_signature(f_variadic, inspect.signature(f_variadic))
    assert SPEC.var_1 == "A"
    assert not hasattr(SPEC, "kw_var_1")  # kw parameters that must be explicitly passed are removed
    assert not hasattr(SPEC, "args")
    fields = SPEC.get_resolvable_fields()
    assert fields == {"var_1": str}


def test_spec_none_when_no_fields() -> None:

    def f_default_only(arg1, arg2=None):
        pass

    SPEC = spec_from_signature(f_default_only, inspect.signature(f_default_only))
    assert SPEC is not None

    del globals()[SPEC.__name__]
    SPEC = spec_from_signature(f_default_only, inspect.signature(f_default_only), include_defaults=False)
    assert SPEC is None

    def f_no_spec(arg1):
        pass

    SPEC = spec_from_signature(f_no_spec, inspect.signature(f_no_spec))
    assert SPEC is None


def f_top_kw_defaults_args(arg1, arg2 = "top", arg3 = dlt.config.value, *args, kw1, kw_lit = "12131", kw_secret_val = dlt.secrets.value, **kwargs):
    pass


def test_argument_have_dlt_config_defaults() -> None:

    def f_defaults(
        req_val, config_val = dlt.config.value, secret_val = dlt.secrets.value, /,
        pos_cf = None, pos_cf_val = dlt.config.value, pos_secret_val = dlt.secrets.value, *,
        kw_val = None, kw_cf_val = dlt.config.value, kw_secret_val = dlt.secrets.value):
        pass

    @with_config
    def f_kw_defaults(*, kw1 = dlt.config.value, kw_lit = "12131", kw_secret_val = dlt.secrets.value, **kwargs):
        pass

    # do not delete those spaces
    @with_config
    # and those comments
    @with_config
    # they are part of the test

    def f_kw_defaults_args(arg1, arg2 = 2, arg3 = dlt.config.value, *args, kw1, kw_lit = "12131", kw_secret_val = dlt.secrets.value, **kwargs):
        pass


    node = get_func_def_node(f_defaults)
    assert node.name == "f_defaults"
    literal_defaults = get_literal_defaults(node)
    assert literal_defaults == {'kw_secret_val': 'dlt.secrets.value', 'kw_cf_val': 'dlt.config.value', 'kw_val': 'None', 'pos_secret_val': 'dlt.secrets.value', 'pos_cf_val': 'dlt.config.value', 'pos_cf': 'None', 'secret_val': 'dlt.secrets.value', 'config_val': 'dlt.config.value'}
    SPEC = spec_from_signature(f_defaults, inspect.signature(f_defaults))
    fields = SPEC.get_resolvable_fields()
    # fields market with dlt config are not optional, same for required fields
    for arg in ["config_val", "secret_val", "pos_cf_val", "pos_secret_val", "kw_cf_val", "kw_secret_val"]:
        assert not is_optional_type(fields[arg])
    for arg in ["pos_cf", "kw_val"]:
        assert is_optional_type(fields[arg])
    # explicit pram does not go into spec
    assert not hasattr(SPEC, "req_val")

    node = get_func_def_node(f_kw_defaults)
    assert node.name == "f_kw_defaults"
    literal_defaults = get_literal_defaults(node)
    assert literal_defaults == {'kw_secret_val': 'dlt.secrets.value', 'kw_lit': "'12131'", "kw1": "dlt.config.value"}
    SPEC = spec_from_signature(f_kw_defaults, inspect.signature(f_kw_defaults))
    fields = SPEC.get_resolvable_fields()
    assert not is_optional_type(fields["kw_lit"])
    assert not is_optional_type(fields["kw1"])
    assert not is_optional_type(fields["kw_secret_val"])

    node = get_func_def_node(f_kw_defaults_args)
    assert node.name == "f_kw_defaults_args"
    literal_defaults = get_literal_defaults(node)
    # print(literal_defaults)
    assert literal_defaults == {'kw_secret_val': 'dlt.secrets.value', 'kw_lit': "'12131'", 'arg3': 'dlt.config.value', 'arg2': '2'}

    node = get_func_def_node(f_top_kw_defaults_args)
    assert node.name == "f_top_kw_defaults_args"
    literal_defaults = get_literal_defaults(node)
    assert literal_defaults == {'kw_secret_val': 'dlt.secrets.value', 'kw_lit': "'12131'", 'arg3': 'dlt.config.value', 'arg2': "'top'"}
