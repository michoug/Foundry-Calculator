/*Copyright 2015-2019 Kirk McDonald

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.*/
"use strict"

function FactoryDef(name, col, row, categories, max_ingredients, speed, moduleSlots, energyUsage, fuel) {
    this.name = name
    this.icon_col = col
    this.icon_row = row
    this.categories = categories
    this.max_ing = max_ingredients
    this.speed = speed
    this.moduleSlots = moduleSlots
    this.energyUsage = energyUsage
    this.fuel = fuel
}
FactoryDef.prototype = {
    constructor: FactoryDef,
    less: function(other) {
        if (!this.speed.equal(other.speed)) {
            return this.speed.less(other.speed)
        }
        return this.moduleSlots < other.moduleSlots
    },
    makeFactory: function(spec, recipe) {
        return new Factory(this, spec, recipe)
    },
    canBeacon: function() {
        return this.moduleSlots > 0
    },
    renderTooltip: function() {
        var t = document.createElement("div")
        t.classList.add("frame")
        var title = document.createElement("h3")
        var im = getImage(this, true)
        title.appendChild(im)
        title.appendChild(new Text(formatName(this.name)))
        t.appendChild(title)
        var b
        if (this.max_ing) {
            b = document.createElement("b")
            b.textContent = "Max ingredients: "
            t.appendChild(b)
            t.appendChild(new Text(this.max_ing))
            t.appendChild(document.createElement("br"))
        }
        b = document.createElement("b")
        b.textContent = "Energy consumption: "
        t.appendChild(b)
        t.appendChild(new Text(alignPower(this.energyUsage, 0)))
        t.appendChild(document.createElement("br"))
        b = document.createElement("b")
        b.textContent = "Crafting speed: "
        t.appendChild(b)
        t.appendChild(new Text(this.speed.toDecimal()))
        // t.appendChild(document.createElement("br"))
        // b = document.createElement("b")
        // b.textContent = "Module slots: "
        // t.appendChild(b)
        // t.appendChild(new Text(this.moduleSlots))
        return t
    }
}

function MinerDef(name, col, row, categories, power, speed, moduleSlots, energyUsage, fuel, overrides) {
    FactoryDef.call(this, name, col, row, categories, 0, 0, moduleSlots, energyUsage, fuel)
    this.mining_power = power
    this.mining_speed = speed
    this.overrides = overrides
}
MinerDef.prototype = Object.create(FactoryDef.prototype)
MinerDef.prototype.less = function(other) {
    if (useLegacyCalculations && !this.mining_power.equal(other.mining_power)) {
        return this.mining_power.less(other.mining_power)
    }
    return this.mining_speed.less(other.mining_speed)
}
MinerDef.prototype.makeFactory = function(spec, recipe) {
    return new Miner(this, spec, recipe)
}
MinerDef.prototype.renderTooltip = function() {
    var t = document.createElement("div")
    t.classList.add("frame")
    var title = document.createElement("h3")
    var im = getImage(this, true)
    title.appendChild(im)
    title.appendChild(new Text(formatName(this.name)))
    t.appendChild(title)
    var b = document.createElement("b")
    b.textContent = "Energy consumption: "
    t.appendChild(b)
    t.appendChild(new Text(alignPower(this.energyUsage, 0)))
    t.appendChild(document.createElement("br"))
    if (useLegacyCalculations) {
        b = document.createElement("b")
        b.textContent = "Mining power: "
        t.appendChild(b)
        t.appendChild(new Text(this.mining_power.toDecimal()))
        t.appendChild(document.createElement("br"))
    }
    b = document.createElement("b")
    b.textContent = "Mining speed: "
    t.appendChild(b)
    t.appendChild(new Text(this.mining_speed.toDecimal()))
    t.appendChild(document.createElement("br"))
    b = document.createElement("b")
    b.textContent = "Module slots: "
    t.appendChild(b)
    t.appendChild(new Text(this.moduleSlots))
    return t
}

function RocketLaunchDef(name, col, row, categories, max_ingredients, speed, moduleSlots, energyUsage, fuel) {
    FactoryDef.call(this, name, col, row, categories, max_ingredients, speed, moduleSlots, energyUsage, fuel)
}
RocketLaunchDef.prototype = Object.create(FactoryDef.prototype)
RocketLaunchDef.prototype.makeFactory = function(spec, recipe) {
    return new RocketLaunch(this, spec, recipe)
}

function RocketSiloDef(name, col, row, categories, max_ingredients, speed, moduleSlots, energyUsage, fuel) {
    FactoryDef.call(this, name, col, row, categories, max_ingredients, speed, moduleSlots, energyUsage, fuel)
}
RocketSiloDef.prototype = Object.create(FactoryDef.prototype)
RocketSiloDef.prototype.makeFactory = function(spec, recipe) {
    return new RocketSilo(this, spec, recipe)
}

function Factory(factoryDef, spec, recipe) {
    this.recipe = recipe
    this.modules = []
    this.setFactory(factoryDef, spec)
    this.beaconModule = spec.defaultBeacon
    this.beaconCount = spec.defaultBeaconCount
}
Factory.prototype = {
    constructor: Factory,
    setFactory: function(factoryDef, spec) {
        this.name = factoryDef.name
        this.factory = factoryDef
        if (this.modules.length > factoryDef.moduleSlots) {
            this.modules.length = factoryDef.moduleSlots
        }
        var toAdd = null
        if (spec.defaultModule && spec.defaultModule.canUse(this.recipe)) {
            toAdd = spec.defaultModule
        }
        while (this.modules.length < factoryDef.moduleSlots) {
            this.modules.push(toAdd)
        }
    },
    getModule: function(index) {
        return this.modules[index]
    },
    // Returns true if the module change requires a recalculation.
    setModule: function(index, module) {
        if (index >= this.modules.length) {
            return false
        }
        var oldModule = this.modules[index]
        var needRecalc = (oldModule && oldModule.hasProdEffect()) || (module && module.hasProdEffect())
        this.modules[index] = module
        return needRecalc
    },
    speedEffect: function(spec) {
        var speed = one
        for (var i=0; i < this.modules.length; i++) {
            var module = this.modules[i]
            if (!module) {
                continue
            }
            speed = speed.add(module.speed)
        }
        if (this.modules.length > 0) {
            var beaconModule = this.beaconModule
            if (beaconModule) {
                speed = speed.add(beaconModule.speed.mul(this.beaconCount).mul(half))
            }
        }
        return speed
    },
    prodEffect: function(spec) {
        var prod = one
        for (var i=0; i < this.modules.length; i++) {
            var module = this.modules[i]
            if (!module) {
                continue
            }
            prod = prod.add(module.productivity)
        }
        return prod
    },
    powerEffect: function(spec) {
        var power = one
        for (var i=0; i < this.modules.length; i++) {
            var module = this.modules[i]
            if (!module) {
                continue
            }
            power = power.add(module.power)
        }
        if (this.modules.length > 0) {
            var beaconModule = this.beaconModule
            if (beaconModule) {
                power = power.add(beaconModule.power.mul(this.beaconCount).mul(half))
            }
        }
        var minimum = RationalFromFloats(1, 5)
        if (power.less(minimum)) {
            power = minimum
        }
        return power
    },
    powerUsage: function(spec, count) {
        var power = this.factory.energyUsage
        if (this.factory.fuel) {
            return {"fuel": this.factory.fuel, "power": power.mul(count)}
        }
        // Default drain value.
        var drain = power.div(RationalFromFloat(30))
        var divmod = count.divmod(one)
        power = power.mul(count)
        if (!divmod.remainder.isZero()) {
            var idle = one.sub(divmod.remainder)
            power = power.add(idle.mul(drain))
        }
        power = power.mul(this.powerEffect(spec))
        return {"fuel": "electric", "power": power}
    },
    recipeRate: function(spec, recipe) {
        return recipe.time.reciprocate().mul(this.factory.speed).mul(this.speedEffect(spec))
    },
    copyModules: function(other, recipe) {
        var length = Math.max(this.modules.length, other.modules.length)
        var needRecalc = false
        for (var i = 0; i < length; i++) {
            var module = this.getModule(i)
            if (!module || module.canUse(recipe)) {
                needRecalc = other.setModule(i, module) || needRecalc
            }
        }
        if (other.factory.canBeacon()) {
            other.beaconModule = this.beaconModule
            other.beaconCount = this.beaconCount
        }
        return needRecalc
    },
}

function Miner(factory, spec, recipe) {
    Factory.call(this, factory, spec, recipe)
}
Miner.prototype = Object.create(Factory.prototype)
Miner.prototype.recipeRate = function(spec, recipe) {
    var miner = this.factory
    var rate
    if (useLegacyCalculations) {
        rate = miner.mining_power.sub(recipe.hardness)
    } else {
        rate = one
    }
    var mining_speed = miner.mining_speed;
    if (recipe.name in miner.overrides) {
        mining_speed = miner.overrides[recipe.name]
    }
    return rate.mul(mining_speed).div(recipe.mining_time).mul(this.speedEffect(spec))
}
Miner.prototype.prodEffect = function(spec) {
    var prod = Factory.prototype.prodEffect.call(this, spec)
    return prod.add(spec.miningProd)
}

var rocketLaunchDuration = RationalFromFloats(2475, 60)

function launchRate(spec) {
    var partRecipe = solver.recipes["rocket-part"]
    var partFactory = spec.getFactory(partRecipe)
    var partItem = solver.items["rocket-part"]
    var gives = partRecipe.gives(partItem, spec)
    // The base rate at which the silo can make rocket parts.
    var rate = Factory.prototype.recipeRate.call(partFactory, spec, partRecipe)
    // Number of times to complete the rocket part recipe per launch.
    var perLaunch = RationalFromFloat(100).div(gives)
    // Total length of time required to launch a rocket.
    var time = perLaunch.div(rate).add(rocketLaunchDuration)
    var launchRate = time.reciprocate()
    var partRate = perLaunch.div(time)
    return {part: partRate, launch: launchRate}
}

function RocketLaunch(factory, spec, recipe) {
    Factory.call(this, factory, spec, recipe)
}
RocketLaunch.prototype = Object.create(Factory.prototype)
RocketLaunch.prototype.recipeRate = function(spec, recipe) {
    return launchRate(spec).launch
}

function RocketSilo(factory, spec, recipe) {
    Factory.call(this, factory, spec, recipe)
}
RocketSilo.prototype = Object.create(Factory.prototype)
RocketSilo.prototype.recipeRate = function(spec, recipe) {
    return launchRate(spec).part
}

var assembly_machine_categories = {
    "assembler": true
}

function compareFactories(a, b) {
    if (a.less(b)) {
        return -1
    }
    if (b.less(a)) {
        return 1
    }
    return 0
}

// Tier detection utilities for mixed tier display
var tierPattern = /^(.+)_(i{1,4})$/

function parseTier(factoryName) {
    // Returns {baseName: string, tier: number} or null
    var match = factoryName.match(tierPattern)
    if (!match) return null
    return {
        baseName: match[1],
        tier: match[2].length // i=1, ii=2, iii=3, iv=4
    }
}

function buildFactoryName(baseName, tier) {
    var roman = ""
    for (var i = 0; i < tier; i++) {
        roman += "i"
    }
    return baseName + "_" + roman
}

function findLowerTierFactory(spec, currentFactory, recipe) {
    var tierInfo = parseTier(currentFactory.name)
    if (!tierInfo || tierInfo.tier <= 1) return null

    var lowerTier = tierInfo.tier - 1
    var lowerName = buildFactoryName(tierInfo.baseName, lowerTier)

    var factories = spec.factories[recipe.category]
    if (!factories) return null

    for (var i = 0; i < factories.length; i++) {
        if (factories[i].name === lowerName) {
            return factories[i]
        }
    }
    return null
}

function shouldUseMixedTier(spec, recipe) {
    if (!mixedTierEnabled) return false
    if (spec.useSmelter(recipe) || spec.useCrusher(recipe)) return false
    return true
}

function calculateMixedTier(spec, recipe, totalCount) {
    if (!shouldUseMixedTier(spec, recipe)) return null

    var currentFactory = spec.getFactory(recipe)
    if (!currentFactory) return null

    var lowerFactory = findLowerTierFactory(spec, currentFactory.factory, recipe)
    if (!lowerFactory) return null

    // Extract integer and fractional parts
    var divmod = totalCount.divmod(one)
    var integerPart = divmod.quotient
    var fractionalPart = divmod.remainder

    // Threshold: fractional >= 0.68 means round up
    var threshold = RationalFromFloats(68, 100)
    if (!fractionalPart.less(threshold)) return null  // >= 0.68

    // Calculate lower tier count
    var speedRatio = lowerFactory.speed.div(currentFactory.factory.speed)
    var lowerCount = fractionalPart.div(speedRatio).ceil()

    return {
        primary: {
            factory: currentFactory.factory,
            count: integerPart
        },
        secondary: {
            factory: lowerFactory,
            count: lowerCount
        }
    }
}

function FactorySpec(factories, tiers) {
    this.spec = {}
    this.factories = {}
    for (var i = 0; i < factories.length; i++) {
        var factory = factories[i]
        for (var j = 0; j < factory.categories.length; j++) {
            var category = factory.categories[j]
            if (!(category in this.factories)) {
                this.factories[category] = []
            }
            this.factories[category].push(factory)
        }
    }
    for (var category in this.factories) {
        this.factories[category].sort(compareFactories)
    }
    this.setMinimum("1")
    var crushers = this.factories["crusher"]
    this.crusher = crushers[0]
    var smelters = this.factories["smelter"].concat(this.factories["advanced_smelter"])
    this.smelter = smelters[0]
    // DEFAULT_FURNACE = this.furnace.name
    this.miningProd = zero
    this.ignore = {}

    this.defaultModule = null
    // XXX: Not used yet.
    this.defaultBeacon = null
    this.defaultBeaconCount = zero
    
    this.tiers = tiers;
    this.metallurgy = tiers[0]
}
FactorySpec.prototype = {
    constructor: FactorySpec,
    // min is a string like "1", "2", or "3".
    setMinimum: function(min) {
        var minIndex = Number(min) - 1
        this.minimum = this.factories["assembler"][minIndex]
    },
    useMinimum: function(recipe) {
        return recipe.category in assembly_machine_categories
    },
    setCrusher: function(name) {
        var crushers = this.factories["crusher"]
        for (var i = 0; i < crushers.length; i++) {
            if (crushers[i].name == name) {
                this.crusher = crushers[i]
                return
            }
        }
    },
    useCrusher: function(recipe) {
        return recipe.category == "crusher"
    },
    setSmelter: function(name) {
        var smelters = this.factories["smelter"]
        for (var i = 0; i < smelters.length; i++) {
            if (smelters[i].name == name) {
                this.smelter = smelters[i]
                return
            }
        }
        smelters = this.factories["advanced_smelter"]
        for (var i = 0; i < smelters.length; i++) {
            if (smelters[i].name == name) {
                this.smelter = smelters[i]
                return
            }
        }
    },
    useSmelter: function(recipe) {
        var categories = Array.isArray(recipe.category) ? recipe.category : [recipe.category]
        for (var i = 0; i < categories.length; i++) {
            if (categories[i] == "smelter" || categories[i] == "advanced_smelter") {
                return true
            }
        }
        return false
    },
    setMetallurgy: function(name) {
        for (var i = 0; i < this.tiers.length; i++) {
            if (this.tiers[i].name == name) {
                this.metallurgy = this.tiers[i]
                for (var j = 0; j < this.tiers.length; j++) {
                    solver.addDisabledRecipes(this.tiers[j].recipes)
                }
                solver.removeDisabledRecipes(this.metallurgy.recipes)
                return
            }
        }
    },
    // recipe.category may be a single category name or an array of tags
    // (e.g. ["casting_machine", "heavy_caster"]). A plain object-key
    // lookup on an array only works by luck for single-element arrays, so
    // union the factories registered under every tag instead.
    getFactoriesForCategory: function(category) {
        if (!Array.isArray(category)) {
            return this.factories[category] || null
        }
        var seen = {}
        var result = []
        for (var i = 0; i < category.length; i++) {
            var factories = this.factories[category[i]]
            if (!factories) {
                continue
            }
            for (var j = 0; j < factories.length; j++) {
                var factoryDef = factories[j]
                if (!seen[factoryDef.name]) {
                    seen[factoryDef.name] = true
                    result.push(factoryDef)
                }
            }
        }
        if (result.length == 0) {
            return null
        }
        result.sort(compareFactories)
        return result
    },
    getFactoryDef: function(recipe) {
        if (this.useCrusher(recipe)) {
            return this.crusher
        }
        if (this.useSmelter(recipe)) {
            var canUseBasicSmelter = false
            if (Array.isArray(recipe.category)) {
                for (var i in recipe.category) {
                    if (recipe.category[i] == "smelter") canUseBasicSmelter = true;
                }
            }
            else {
                if (recipe.category == "smelter") canUseBasicSmelter = true;
            }
            if (!canUseBasicSmelter) {
                return this.factories["advanced_smelter"][0]
            }
            return this.smelter
        }
        var factories = this.getFactoriesForCategory(recipe.category)
        if (!factories) {
            return null
        }
        if (!this.useMinimum(recipe)) {
            return factories[factories.length - 1]
        }
        var factoryDef
        for (var i = 0; i < factories.length; i++) {
            factoryDef = factories[i]
            if (factoryDef.less(this.minimum) || useLegacyCalculations && factoryDef.max_ing < recipe.ingredients.length) {
                continue
            }
            break
        }
        return factoryDef
    },
    // TODO: This should be very cheap. Calling getFactoryDef on each call
    // should not be necessary. Changing the minimum should proactively update
    // all of the factories to which it applies.
    getFactory: function(recipe) {
        if (!recipe.category) {
            return null
        }
        var factoryDef = this.getFactoryDef(recipe)
        if (!factoryDef) {
            return null
        }
        var factory = this.spec[recipe.name]
        // If the minimum changes, update the factory the next time we get it.
        if (factory) {
            factory.setFactory(factoryDef, this)
            return factory
        }
        this.spec[recipe.name] = factoryDef.makeFactory(this, recipe)
        this.spec[recipe.name].beaconCount = this.defaultBeaconCount
        return this.spec[recipe.name]
    },
    moduleCount: function(recipe) {
        var factory = this.getFactory(recipe)
        if (!factory) {
            return 0
        }
        return factory.modules.length
    },
    getModule: function(recipe, index) {
        var factory = this.getFactory(recipe)
        var module = factory.getModule(index)
        return module
    },
    setModule: function(recipe, index, module) {
        var factory = this.getFactory(recipe)
        if (!factory) {
            return false
        }
        return factory.setModule(index, module)
    },
    getBeaconInfo: function(recipe) {
        var factory = this.getFactory(recipe)
        var module = factory.beaconModule
        return {"module": module, "count": factory.beaconCount}
    },
    setDefaultModule: function(module) {
        // Set anything set to the old default to the new.
        for (var recipeName in this.spec) {
            var factory = this.spec[recipeName]
            var recipe = factory.recipe
            for (var i = 0; i < factory.modules.length; i++) {
                if (factory.modules[i] === this.defaultModule && (!module || module.canUse(recipe))) {
                    factory.modules[i] = module
                }
            }
        }
        this.defaultModule = module
    },
    setDefaultBeacon: function(module, count) {
        for (var recipeName in this.spec) {
            var factory = this.spec[recipeName]
            var recipe = factory.recipe
            // Set anything set to the old defeault beacon module to the new.
            if (factory.beaconModule === this.defaultBeacon && (!module || module.canUse(recipe))) {
                factory.beaconModule = module
            }
            // Set any beacon counts equal to the old default to the new one.
            if (factory.beaconCount.equal(this.defaultBeaconCount)) {
                factory.beaconCount = count
            }
        }
        this.defaultBeacon = module
        this.defaultBeaconCount = count
    },
    getCount: function(recipe, rate) {
        var factory = this.getFactory(recipe)
        if (!factory) {
            return zero
        }
        return rate.div(factory.recipeRate(this, recipe))
    },
    recipeRate: function(recipe) {
        var factory = this.getFactory(recipe)
        if (!factory) {
            return null
        }
        return factory.recipeRate(this, recipe)
    },
}

function renderTooltipBase() {
    var t = document.createElement("div")
    t.classList.add("frame")
    var title = document.createElement("h3")
    var im = getImage(this, true)
    title.appendChild(im)
    title.appendChild(new Text(formatName(this.name)))
    t.appendChild(title)
    return t
}

function getFactories(data) {
    var factories = []
    for (var name in data["machine"]) {
        var d = data["machine"][name]
        var fuel = null
        if (d.energy_source && d.energy_source.type === "burner") {
            fuel = d.energy_source.fuel_category
        }
        factories.push(new FactoryDef(
            d.name,
            d.icon_col,
            d.icon_row,
            d.crafting_categories,
            d.ingredient_count,
            RationalFromFloat(d.crafting_speed),
            d.module_slots,
            RationalFromFloat(d.energy_usage),
            fuel
        ))
    }
    for (var name in data["miners"]) {
        var d = data["miners"][name]
        var fuel = null
        if (d.energy_source && d.energy_source.type === "burner") {
            fuel = d.energy_source.fuel_category
        }
        var power
        if (d.mining_power) {
            power = RationalFromFloat(d.mining_power)
        } else {
            power = null
        }
        var overrides = {}
        for (var oname in d.overrides) {
            overrides[oname] = RationalFromFloats(d.overrides[oname], 60)
        }
        factories.push(new MinerDef(
            d.name,
            d.icon_col,
            d.icon_row,
            d.crafting_categories,
            power,
            RationalFromFloats(d.mining_speed, 60.0),
            d.module_slots,
            RationalFromFloat(d.energy_usage),
            fuel,
            overrides
        ))
    }
    return factories
}
